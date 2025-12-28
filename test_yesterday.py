#!/usr/bin/env python3
"""Test script to fetch yesterday's data."""
import asyncio
import json
import sys
from datetime import datetime, timedelta

import aiohttp


async def test_yesterday_data(username: str, password: str, device_id: str = "86180"):
    """Test fetching yesterday's complete data."""
    print(f"Testing data fetch for YESTERDAY")
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
            # Check if we're still on login page (failed auth)
            if "login" in final_url and response.status != 200:
                print(f"❌ Login failed - still on login page")
                return
            # Both pnd.cezdistribuce.cz and dip.cezdistribuce.cz are valid redirects
            if "cezdistribuce.cz" not in final_url:
                print(f"❌ Login failed - unexpected redirect: {response.url}")
                return

        print("✅ Authenticated successfully\n")

        # Step 2: Fetch YESTERDAY's data (complete day)
        yesterday = datetime.now() - timedelta(days=1)
        start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0)
        end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59)

        date_format = "%d.%m.%Y %H:%M"
        interval_from = start_of_yesterday.strftime(date_format)
        interval_to = end_of_yesterday.strftime(date_format)

        print(f"2. Fetching data for YESTERDAY:")
        print(f"   Date: {yesterday.strftime('%d.%m.%Y')} ({yesterday.strftime('%A')})")
        print(f"   From: {interval_from}")
        print(f"   To:   {interval_to}\n")

        # Fetch consumption
        print("=" * 80)
        print("CONSUMPTION DATA (Yesterday)")
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

                    # Show data points if available
                    if series.get("data"):
                        print(f"\n📈 Data points: {len(series['data'])} measurement(s)")
                        for i, point in enumerate(series["data"][:5], 1):  # Show first 5
                            timestamp, value, status = point[0], point[1], point[2] if len(point) > 2 else "N/A"
                            print(f"   {i}. {timestamp}: {value:.3f} kWh ({status})")
                        if len(series["data"]) > 5:
                            print(f"   ... and {len(series['data']) - 5} more")
                else:
                    print("❌ No consumption data available for yesterday")
            else:
                print(f"❌ Failed to fetch consumption data: {response.status}")

        # Fetch production
        print("\n" + "=" * 80)
        print("PRODUCTION DATA (Yesterday)")
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

                    # Show data points if available
                    if series.get("data"):
                        print(f"\n📈 Data points: {len(series['data'])} measurement(s)")
                        for i, point in enumerate(series["data"][:5], 1):  # Show first 5
                            timestamp, value, status = point[0], point[1], point[2] if len(point) > 2 else "N/A"
                            print(f"   {i}. {timestamp}: {value:.3f} kWh ({status})")
                        if len(series["data"]) > 5:
                            print(f"   ... and {len(series['data']) - 5} more")
                else:
                    print("❌ No production data available for yesterday")
            else:
                print(f"❌ Failed to fetch production data: {response.status}")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\nThis is what the Home Assistant integration will show:")
        print("• sensor.cez_pnd_energy_consumption")
        print("• sensor.cez_pnd_energy_production")
        print("\nThese sensors will update every hour with the latest available data.")
        print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_yesterday.py <username> <password> [device_id]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    device_id = sys.argv[3] if len(sys.argv) > 3 else "86180"

    asyncio.run(test_yesterday_data(username, password, device_id))
