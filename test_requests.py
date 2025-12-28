#!/usr/bin/env python3
"""Test script using requests library like the working ČEZ integration."""
import json
import sys
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup


def test_with_requests(username: str, password: str, device_id: str = "86180"):
    """Test with requests.Session() like the working integration."""
    print(f"Testing with requests.Session for user: {username}")
    print("-" * 50)

    # Create session like the working integration does
    session = requests.Session()
    session.max_redirects = 10

    try:
        # Step 1: Get OAuth2 authorization URL
        print("\n1. Getting OAuth2 authorization URL...")
        response = session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        )
        service_url = response.url
        print(f"   Status: {response.status_code}")
        print(f"   CAS Login URL: {service_url}")

        # Extract execution token using BeautifulSoup like the working integration
        soup = BeautifulSoup(response.text, 'html.parser')
        execution = soup.find('input', {'name': 'execution'})['value']
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

        response = session.post(
            service_url,
            data=login_data,
            allow_redirects=True,
        )
        print(f"   Status: {response.status_code}")
        print(f"   Final URL: {response.url}")
        print(f"   ✅ Authentication successful")
        print(f"   Cookies: {len(session.cookies)}")

        # Step 3: Access dashboard
        print("\n3. Accessing dashboard...")
        response = session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view",
            allow_redirects=True,
        )
        print(f"   Status: {response.status_code}")
        print(f"   Final URL: {response.url}")
        print(f"   Cookies after dashboard: {len(session.cookies)}")

        # Step 4: Fetch data
        print("\n4. Fetching data...")

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

        response = session.post(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/data",
            json=payload,
            allow_redirects=False,
        )

        print(f"   Status: {response.status_code}")
        print(f"   URL: {response.url}")

        if response.status_code == 302:
            print(f"   ❌ Got 302 redirect")
            print(f"   Location: {response.headers.get('Location', 'unknown')}")
        elif response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Data received successfully")
                if data.get('hasData'):
                    print(f"   Total: {data['seriesStats'][0].get('total', 'N/A')}")
                    print(f"   Data points: {len(data['series'][0]['data'])}")
            except Exception as e:
                print(f"   ❌ Error parsing response: {e}")
                print(f"   Response text: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


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

    test_with_requests(username, password, device_id)
