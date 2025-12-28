#!/usr/bin/env python3
"""Verbose test script to debug login issues."""
import asyncio
import re
import sys

import aiohttp


async def test_login(username: str, password: str):
    """Test login with verbose output."""
    print(f"Testing login for: {username}")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        # Step 1: Get the login form
        print("\n1. Fetching login form...")
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        ) as response:
            service_url = str(response.url)
            html = await response.text()

            print(f"Service URL: {service_url}\n")

            # Extract execution token
            execution_match = re.search(r'name="execution"\s+value="([^"]+)"', html)
            execution = execution_match.group(1) if execution_match else None

            if not execution:
                print("❌ Failed to extract execution token!")
                return False

            print(f"✓ Extracted execution token (length: {len(execution)})\n")

        # Step 2: Submit the login form
        print("2. Submitting credentials...")
        login_data = {
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": "",
        }

        print(f"Form data:")
        for key, value in login_data.items():
            if key == "password":
                print(f"  {key}: ****")
            elif key == "execution":
                print(f"  {key}: {value[:50]}...")
            else:
                print(f"  {key}: {value}")

        # Set proper headers for form submission
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": service_url,
        }

        async with session.post(
            service_url,
            data=login_data,
            headers=headers,
            allow_redirects=False,  # Don't follow redirects automatically
        ) as response:
            print(f"\nResponse status: {response.status}")
            print(f"Response headers:")
            for key, value in response.headers.items():
                if key.lower() in ["location", "set-cookie", "content-type"]:
                    print(f"  {key}: {value}")

            if response.status == 302:
                location = response.headers.get("Location", "")
                print(f"\n✓ Redirect to: {location}")

                if "login" in location.lower() and "error" in location.lower():
                    print("❌ Login failed - redirected to login with error")
                    return False
                elif "pnd.cezdistribuce.cz" in location.lower():
                    print("✓ Looks like successful login!")
                    return True
                else:
                    print("? Unexpected redirect")

            elif response.status == 401:
                html = await response.text()
                # Look for error messages
                error_match = re.search(r'<div class="formError"[^>]*>([^<]+)</div>', html)
                if error_match:
                    print(f"❌ Login error: {error_match.group(1)}")
                else:
                    print("❌ 401 Unauthorized - credentials might be wrong")
                return False

            else:
                text = await response.text()
                print(f"\nResponse body (first 500 chars):\n{text[:500]}")
                return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_login_verbose.py <username> <password>")
        sys.exit(1)

    asyncio.run(test_login(sys.argv[1], sys.argv[2]))
