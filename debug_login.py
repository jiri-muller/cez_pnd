#!/usr/bin/env python3
"""Debug script to inspect the login form."""
import asyncio
import re

import aiohttp


async def inspect_login_form():
    """Inspect the login form to see what fields it expects."""
    async with aiohttp.ClientSession() as session:
        # Get the OAuth authorization page
        print("Fetching OAuth authorization page...")
        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        ) as response:
            service_url = str(response.url)
            html = await response.text()

            print(f"\nService URL: {service_url}")
            print("\n" + "=" * 80)
            print("LOGIN FORM HTML:")
            print("=" * 80)

            # Find the form
            form_match = re.search(r'<form[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
            if form_match:
                form_html = form_match.group(0)
                print(form_html)

                # Find all input fields
                print("\n" + "=" * 80)
                print("INPUT FIELDS:")
                print("=" * 80)
                inputs = re.findall(r'<input[^>]*>', form_html, re.IGNORECASE)
                for inp in inputs:
                    # Extract name and value
                    name_match = re.search(r'name="([^"]*)"', inp)
                    value_match = re.search(r'value="([^"]*)"', inp)
                    type_match = re.search(r'type="([^"]*)"', inp)

                    name = name_match.group(1) if name_match else "NO NAME"
                    value = value_match.group(1) if value_match else "NO VALUE"
                    input_type = type_match.group(1) if type_match else "text"

                    print(f"  {input_type:10} | name='{name:20}' | value='{value}'")
            else:
                print("No form found! Here's the full HTML:")
                print(html[:2000])


if __name__ == "__main__":
    asyncio.run(inspect_login_form())
