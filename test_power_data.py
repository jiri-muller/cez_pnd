#!/usr/bin/env python3
"""Test script for 15-minute power data."""
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

# Read credentials
with open("credentials.txt", "r") as f:
    lines = f.readlines()
    username = lines[0].strip().split(": ")[1]
    password = lines[1].strip().split(": ")[1]
    device_id = lines[2].strip().split(": ")[1] if len(lines) > 2 else "86180"

API_BASE_URL = "https://pnd.cezdistribuce.cz/cezpnd2"
API_DATA_URL = f"{API_BASE_URL}/external/data"
ID_ASSEMBLY_CONSUMPTION_POWER = -1001
ID_ASSEMBLY_PRODUCTION_POWER = -1002

session = requests.Session()
session.max_redirects = 10

# Authenticate
print("Authenticating...")
response = session.get(f"{API_BASE_URL}/oauth2/authorization/mepas-external", allow_redirects=True)
soup = BeautifulSoup(response.text, 'html.parser')
execution = soup.find('input', {'name': 'execution'})['value']

login_data = {
    "username": username,
    "password": password,
    "execution": execution,
    "_eventId": "submit",
    "geolocation": "",
}
response = session.post(response.url, data=login_data, allow_redirects=True)
response = session.get(f"{API_BASE_URL}/external/dashboard/view", allow_redirects=True)

# Fetch today's 15-minute power data
now = datetime.now()
date_format = "%d.%m.%Y %H:%M"
today = now.replace(hour=0, minute=0, second=0, microsecond=0)
today_from = today.strftime(date_format)
today_to = now.replace(hour=23, minute=59, second=59).strftime(date_format)

print(f"\nFetching consumption power: {today_from} - {today_to}")

payload = {
    "format": "chart",
    "idAssembly": ID_ASSEMBLY_CONSUMPTION_POWER,
    "idDeviceSet": device_id,
    "intervalFrom": today_from,
    "intervalTo": today_to,
    "compareFrom": None,
    "opmId": None,
    "electrometerId": None,
}

response = session.post(API_DATA_URL, json=payload, allow_redirects=False)
data = response.json()

print("\n=== RAW API RESPONSE (first 5 data points) ===")
if data.get("hasData") and data.get("series"):
    series = data["series"][0]
    raw_data = series.get("data", [])

    print(f"Total data points: {len(raw_data)}")
    print(f"Unit: {data.get('unitY')}")
    print("\nFirst 5 measurements:")
    for point in raw_data[:5]:
        print(f"  {point}")

print("\n=== PROCESSED DATA (like integration does) ===")
if data.get("hasData") and data.get("series"):
    series = data["series"][0]
    stats = data["seriesStats"][0] if data.get("seriesStats") else {}
    raw_data = series.get("data", [])

    # Filter out invalid data points
    valid_data = []
    for point in raw_data:
        if len(point) >= 3 and point[2] == "naměřená data OK":
            valid_data.append({
                "timestamp": point[0],
                "value": float(point[1]),
            })

    # Get the latest valid measurement
    current_power = 0.0
    latest_timestamp = ""
    if valid_data:
        latest = valid_data[-1]
        current_power = latest["value"]
        latest_timestamp = latest["timestamp"]

    result = {
        "current": current_power,
        "latest_timestamp": latest_timestamp,
        "valid_measurements_count": len(valid_data),
        "total_measurements": len(raw_data),
        "min": stats.get("min", "N/A"),
        "max": stats.get("max", "N/A"),
        "total_energy": stats.get("total", "N/A"),
        "name": series.get("name", ""),
        "unit": data.get("unitY", "kW"),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n=== SENSOR WOULD SHOW ===")
    print(f"State (current power): {result['current']} kW")
    print(f"Latest measurement: {result['latest_timestamp']}")
    print(f"Valid measurements: {result['valid_measurements_count']} / {result['total_measurements']}")
    print(f"Min: {result['min']} kW, Max: {result['max']} kW")
    print(f"Total energy today: {result['total_energy']} kWh")

    print("\n=== Last 5 valid measurements ===")
    for m in valid_data[-5:]:
        print(f"  {m['timestamp']}: {m['value']} kW")
else:
    print("NO DATA!")

session.close()
