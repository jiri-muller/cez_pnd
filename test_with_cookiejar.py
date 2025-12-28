#!/usr/bin/env python3
"""Test script that mimics the exact API implementation with CookieJar."""
import asyncio
import json
import sys
from datetime import datetime, timedelta
import aiohttp


async def test_with_cookiejar(username: str, password: str, device_id: str = "86180"):
    """Test with the exact same session setup as the API."""
    print(f"Testing with CookieJar for user: {username}")
    print("-" * 50)

    # Create session exactly like the API does
    cookie_jar = aiohttp.CookieJar(unsafe=True)
    timeout = aiohttp.ClientTimeout(total=30)
    session = aiohttp.ClientSession(
        cookie_jar=cookie_jar,
        timeout=timeout,
    )

    try:
        # Step 1: Get OAuth2 authorization URL
        print("\n1. Getting OAuth2 authorization URL...")
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            service_url = str(response.url)
            html = await response.text()
            print(f"   Status: {response.status}")
            print(f"   CAS Login URL: {service_url}")

            # Extract execution token
            import re
            execution_match = re.search(r'name="execution"\s+value="([^"]+)"', html)
            execution = execution_match.group(1) if execution_match else None

            if not execution:
                print("   ❌ Failed to extract execution token")
                return

            print(f"   Execution token length: {len(execution)}")

        # Step 2: Perform login
        print("\n2. Attempting login...")
        login_data = {
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": "",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": service_url,
            "Origin": "https://cas.cez.cz",
        }

        async with session.post(
            service_url,
            data=login_data,
            headers=headers,
            allow_redirects=True,
        ) as response:
            print(f"   Status: {response.status}")
            print(f"   Final URL: {response.url}")

            final_url = str(response.url).lower()
            if "cezdistribuce.cz" not in final_url:
                print(f"   ❌ Unexpected redirect: {response.url}")
                return

            print(f"   ✅ Authentication successful")
            print(f"   Cookies in jar: {len(session.cookie_jar)}")

        # Step 3: Try to fetch data
        print("\n3. Fetching data...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        date_format = "%d.%m.%Y %H:%M"
        interval_from = start_date.replace(hour=0, minute=0, second=0).strftime(date_format)
        interval_to = start_date.replace(hour=23, minute=59, second=59).strftime(date_format)

        payload = {
            "format": "chart",
            "idAssembly": -1021,
            "idDeviceSet": device_id,
            "intervalFrom": interval_from,
            "intervalTo": interval_to,
            "compareFrom": "",
            "opmId": None,
            "electrometerId": None,
        }

        print(f"   Date range: {interval_from} to {interval_to}")
        print(f"   Cookies before POST: {len(session.cookie_jar)}")
        for cookie in session.cookie_jar:
            print(f"   Cookie: {cookie.key} for domain {cookie.get('domain', 'no-domain')}")

        async with session.post(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/data",
            json=payload,
            allow_redirects=False,  # Same as API
        ) as response:
            print(f"   Status: {response.status}")
            print(f"   URL: {response.url}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")

            if response.status == 302:
                print(f"   ❌ Got 302 redirect - cookies not being sent!")
                redirect_location = response.headers.get('Location', 'unknown')
                print(f"   Redirect location: {redirect_location}")
            elif response.status == 200:
                try:
                    data = await response.json()
                    print(f"   ✅ Data received successfully")
                    print(f"   {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                except Exception as e:
                    print(f"   ❌ Error parsing response: {e}")
                    text = await response.text()
                    print(f"   Response text: {text[:200]}")
            else:
                text = await response.text()
                print(f"   Response: {text[:200]}")

    finally:
        await session.close()


if __name__ == "__main__":
    # Read credentials
    try:
        with open("credentials.txt", "r") as f:
            lines = f.readlines()
            username = lines[0].strip().split(": ")[1]
            password = lines[1].strip().split(": ")[1]
            device_id = lines[2].strip().split(": ")[1] if len(lines) > 2 else "86180"
    except Exception as e:
        print(f"Error reading credentials: {e}")
        sys.exit(1)

    asyncio.run(test_with_cookiejar(username, password, device_id))
