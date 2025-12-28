#!/usr/bin/env python3
"""Test script to fetch data for a specific date."""
import asyncio
import sys
from datetime import datetime

import aiohttp


async def test_specific_date(username: str, password: str, date_str: str, device_id: str = "86180"):
    """Test fetching data for a specific date."""
    try:
        # Parse the date
        target_date = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        print(f"❌ Invalid date format. Use DD.MM.YYYY (e.g., 10.12.2025)")
        return

    print(f"Testing data fetch for: {target_date.strftime('%d.%m.%Y')} ({target_date.strftime('%A')})")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        # Step 1: Authenticate
        print("\n1. Authenticating...")
        import re

        async with session.get(
            "https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external",
            allow_redirects=True,
        ) as response:
            service_url = str(response.url)
            html = await response.text()
            execution_match = re.search(r'name="execution"\s+value="([^"]+)"', html)
            execution = execution_match.group(1) if execution_match else None

        if not execution:
            print("❌ Failed to extract execution token")
            return

        login_data = {
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": "",
        }

        async with session.post(
            service_url,
            data=login_data,
            allow_redirects=True,
        ) as response:
            final_url = str(response.url).lower()
            if "login" in final_url and response.status != 200:
                print(f"❌ Login failed")
                return
            if "cezdistribuce.cz" not in final_url:
                print(f"❌ Login failed - unexpected redirect")
                return

        print("✅ Authenticated successfully\n")

        # Step 2: Fetch data for specific date
        start_of_day = target_date.replace(hour=0, minute=0, second=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59)

        date_format = "%d.%m.%Y %H:%M"
        interval_from = start_of_day.strftime(date_format)
        interval_to = end_of_day.strftime(date_format)

        print(f"2. Fetching data for: {target_date.strftime('%d.%m.%Y')}")
        print(f"   From: {interval_from}")
        print(f"   To:   {interval_to}\n")

        # Fetch consumption
        print("=" * 80)
        print("CONSUMPTION DATA")
        print("=" * 80)

        payload_consumption = {
            "format": "chart",
            "idAssembly": -1021,
            "idDeviceSet": device_id,
            "intervalFrom": interval_from,
            "intervalTo": interval_to,
            "compareFrom": "",
            "opmId": None,
            "electrometerId": None,
        }

        async with session.post(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/data",
            json=payload_consumption,
        ) as response:
            if response.status == 200:
                data = await response.json()

                if data.get("hasData") and data.get("series"):
                    series = data["series"][0]
                    stats = data["seriesStats"][0] if data.get("seriesStats") else {}

                    print(f"\n📊 Meter: {series.get('name', 'N/A')}")
                    print(f"📅 Period: {stats.get('dateFrom', 'N/A')} - {stats.get('dateTo', 'N/A')}")
                    print(f"\n⚡ TOTAL CONSUMPTION: {stats.get('total', '0')} {data.get('unitY', 'kWh')}")
                    print(f"   Min: {stats.get('min', '0')} {data.get('unitY', 'kWh')}")
                    print(f"   Max: {stats.get('max', '0')} {data.get('unitY', 'kWh')}")

                    if series.get("data"):
                        print(f"\n📈 Data points: {len(series['data'])} measurement(s)")
                        for i, point in enumerate(series["data"][:10], 1):
                            timestamp, value, status = point[0], point[1], point[2] if len(point) > 2 else "N/A"
                            print(f"   {i}. {timestamp}: {value:.3f} kWh ({status})")
                        if len(series["data"]) > 10:
                            print(f"   ... and {len(series['data']) - 10} more")
                else:
                    print("❌ No consumption data available for this date")
                    print(f"   Response: {data}")
            else:
                print(f"❌ Failed to fetch consumption data: {response.status}")

        # Fetch production
        print("\n" + "=" * 80)
        print("PRODUCTION DATA")
        print("=" * 80)

        payload_production = {
            "format": "chart",
            "idAssembly": -1022,
            "idDeviceSet": device_id,
            "intervalFrom": interval_from,
            "intervalTo": interval_to,
            "compareFrom": "",
            "opmId": None,
            "electrometerId": None,
        }

        async with session.post(
            "https://pnd.cezdistribuce.cz/cezpnd2/external/data",
            json=payload_production,
        ) as response:
            if response.status == 200:
                data = await response.json()

                if data.get("hasData") and data.get("series"):
                    series = data["series"][0]
                    stats = data["seriesStats"][0] if data.get("seriesStats") else {}

                    print(f"\n📊 Meter: {series.get('name', 'N/A')}")
                    print(f"📅 Period: {stats.get('dateFrom', 'N/A')} - {stats.get('dateTo', 'N/A')}")
                    print(f"\n☀️  TOTAL PRODUCTION: {stats.get('total', '0')} {data.get('unitY', 'kWh')}")
                    print(f"   Min: {stats.get('min', '0')} {data.get('unitY', 'kWh')}")
                    print(f"   Max: {stats.get('max', '0')} {data.get('unitY', 'kWh')}")

                    if series.get("data"):
                        print(f"\n📈 Data points: {len(series['data'])} measurement(s)")
                        for i, point in enumerate(series["data"][:10], 1):
                            timestamp, value, status = point[0], point[1], point[2] if len(point) > 2 else "N/A"
                            print(f"   {i}. {timestamp}: {value:.3f} kWh ({status})")
                        if len(series["data"]) > 10:
                            print(f"   ... and {len(series['data']) - 10} more")
                else:
                    print("❌ No production data available for this date")
                    print(f"   Response: {data}")
            else:
                print(f"❌ Failed to fetch production data: {response.status}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python test_specific_date.py <username> <password> <date> [device_id]")
        print("Example: python test_specific_date.py user@email.com password 10.12.2025")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    date_str = sys.argv[3]
    device_id = sys.argv[4] if len(sys.argv) > 4 else "86180"

    asyncio.run(test_specific_date(username, password, date_str, device_id))
