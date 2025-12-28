#!/usr/bin/env python3
"""Simplest possible login test."""
import asyncio
import re
import sys
from urllib.parse import urlencode

import aiohttp


async def test(username, password):
    """Simple login test."""
    async with aiohttp.ClientSession() as session:
        # Get login form
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        ) as resp:
            url = str(resp.url)
            html = await resp.text()

            # Extract execution
            match = re.search(r'name="execution"\s+value="([^"]+)"', html)
            execution = match.group(1) if match else None

            if not execution:
                print("No execution token found")
                return

            print(f"Login URL: {url}")
            print(f"Execution: {execution[:50]}...")

        # Login
        data = {
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": ""
        }

        print(f"\nForm data being sent:")
        print(urlencode(data)[:200])

        async with session.post(url, data=data, allow_redirects=False) as resp:
            print(f"\nStatus: {resp.status}")
            location = resp.headers.get("Location", "")
            print(f"Location: {location}")

            if resp.status in [301, 302, 303]:
                if "error" in location.lower():
                    print("ERROR in redirect")
                elif "pnd.cezdistribuce.cz" in location:
                    print("SUCCESS! Redirect to PND")

                    # Follow the redirect
                    async with session.get(location if location.startswith("http") else "https://cas.cez.cz" + location, allow_redirects=True) as resp2:
                        print(f"Final URL: {resp2.url}")
                        if "dashboard" in str(resp2.url):
                            print("✓✓✓ Logged in successfully!")
                            return True
            elif resp.status == 401:
                body = await resp.text()
                error = re.search(r'<div class="formError"[^>]*>([^<]+)</div>', body)
                if error:
                    print(f"Error message: {error.group(1)}")
                # Check for all form errors
                errors = re.findall(r'<div class="formError"[^>]*>([^<]+)</div>', body)
                if errors:
                    print(f"All errors: {errors}")

    return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: script.py username password")
        sys.exit(1)

    result = asyncio.run(test(sys.argv[1], sys.argv[2]))
    sys.exit(0 if result else 1)
