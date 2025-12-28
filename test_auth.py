#!/usr/bin/env python3
"""Test script for ČEZ PND authentication and data fetching."""
import asyncio
import json
import sys
from datetime import datetime, timedelta

import aiohttp


async def test_auth(username: str, password: str, device_id: str = "86180"):
    """Test authentication and data fetching."""
    print(f"Testing authentication for user: {username}")
    print("-" * 50)

    async with aiohttp.ClientSession() as session:
        # Step 1: Get OAuth2 authorization URL
        print("\n1. Getting OAuth2 authorization URL...")
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        ) as response:
            print(f"   Status: {response.status}")
            print(f"   Final URL: {response.url}")

        # Step 2: Try to login via CAS
        print("\n2. Attempting CAS login...")

        # Get the login page to extract the execution token and form action URL
        import re
        service_url = None
        execution = None
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        ) as response:
            service_url = str(response.url)
            html = await response.text()

            # Extract execution token
            execution_match = re.search(r'name="execution"\s+value="([^"]+)"', html)
            execution = execution_match.group(1) if execution_match else None

            # Extract form action
            form_action_match = re.search(r'<form[^>]+action="([^"]+)"', html)
            form_action = form_action_match.group(1) if form_action_match else "login"

            print(f"   Service URL: {service_url}")
            print(f"   Form action: {form_action}")
            print(f"   Execution token: {execution[:50]}..." if execution else "None")

        if not execution:
            print("   ❌ Failed to extract execution token")
            return False

        login_data = {
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": "",
        }

        # The form action is relative, but we need to keep the service parameter from service_url
        # The form posts to just "login" but we need the full URL with the service parameter
        print(f"   Posting to: {service_url}")

        async with session.post(
            service_url,  # Post back to the same URL with the service parameter
            data=login_data,
            allow_redirects=True,
        ) as response:
            print(f"   Login status: {response.status}")
            print(f"   Final URL: {response.url}")

            if response.status >= 400:
                text = await response.text()
                print(f"   Error response: {text[:500]}")

            if "login" in str(response.url).lower():
                print("   ❌ Authentication FAILED - still on login page")
                return False
            else:
                print("   ✅ Authentication appears successful")

        # Step 3: Try to access the dashboard
        print("\n3. Accessing dashboard...")
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view",
            allow_redirects=True,
        ) as response:
            print(f"   Status: {response.status}")
            print(f"   URL: {response.url}")

            if "login" in str(response.url).lower():
                print("   ❌ Not authenticated - redirected to login")
                return False
            else:
                print("   ✅ Dashboard accessible")

        # Step 4: Fetch consumption data
        print("\n4. Fetching consumption data...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        date_format = "%d.%m.%Y %H:%M"
        interval_from = start_date.strftime(date_format).replace(" 00:00", " 00:00")
        interval_to = end_date.strftime(date_format).replace(" 00:00", " 00:00")

        payload = {
            "format": "chart",
            "idAssembly": -1021,  # Consumption
            "idDeviceSet": device_id,
            "intervalFrom": interval_from,
            "intervalTo": interval_to,
            "compareFrom": "",
            "opmId": None,
            "electrometerId": None,
        }

        print(f"   Payload: {json.dumps(payload, indent=2)}")

        async with session.post(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/data",
            json=payload,
        ) as response:
            print(f"   Status: {response.status}")

            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Consumption data received:")
                print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"   ❌ Failed to fetch data")
                text = await response.text()
                print(f"   Response: {text[:500]}")

        # Step 5: Fetch production data
        print("\n5. Fetching production data...")
        payload["idAssembly"] = -1022  # Production

        async with session.post(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/data",
            json=payload,
        ) as response:
            print(f"   Status: {response.status}")

            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Production data received:")
                print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"   ❌ Failed to fetch data")

        print("\n" + "=" * 50)
        print("Test completed!")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_auth.py <username> <password> [device_id]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    device_id = sys.argv[3] if len(sys.argv) > 3 else "86180"

    asyncio.run(test_auth(username, password, device_id))
