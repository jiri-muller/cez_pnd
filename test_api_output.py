#!/usr/bin/env python3
"""Test script to see the exact API output structure."""
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
ID_ASSEMBLY_CONSUMPTION = -1021

def parse_czech_number(value):
    """Parse Czech number format."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(",", ".").replace(" ", "")
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0

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

# Fetch today's consumption
now = datetime.now()
date_format = "%d.%m.%Y %H:%M"
today = now.replace(hour=0, minute=0, second=0, microsecond=0)
today_from = today.strftime(date_format)
today_to = now.replace(hour=23, minute=59, second=59).strftime(date_format)

payload = {
    "format": "chart",
    "idAssembly": ID_ASSEMBLY_CONSUMPTION,
    "idDeviceSet": device_id,
    "intervalFrom": today_from,
    "intervalTo": today_to,
    "compareFrom": "",
    "opmId": None,
    "electrometerId": None,
}

print(f"\nFetching consumption today: {today_from} - {today_to}")
response = session.post(API_DATA_URL, json=payload, allow_redirects=False)
data = response.json()

print("\n=== RAW API RESPONSE ===")
print(json.dumps(data, indent=2, ensure_ascii=False))

print("\n=== PROCESSED DATA (like API does) ===")
if data.get("hasData") and data.get("series"):
    series = data["series"][0]
    stats = data["seriesStats"][0] if data.get("seriesStats") else {}

    last_value = 0.0
    if series.get("data") and len(series["data"]) > 0:
        last_data_point = series["data"][-1]
        if len(last_data_point) >= 2:
            last_value = float(last_data_point[1])

    result = {
        "value": last_value,
        "total": parse_czech_number(stats.get("total", "0")),
        "min": parse_czech_number(stats.get("min", "0")),
        "max": parse_czech_number(stats.get("max", "0")),
        "name": series.get("name", ""),
        "unit": data.get("unitY", "kWh"),
        "date_from": stats.get("dateFrom", ""),
        "date_to": stats.get("dateTo", ""),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n=== SENSOR WOULD SHOW ===")
    print(f"State (native_value): {result['total']}")
    print(f"Unit: {result['unit']}")
    print(f"Attributes:")
    print(f"  last_value: {result['value']}")
    print(f"  min: {result['min']}")
    print(f"  max: {result['max']}")
    print(f"  meter_name: {result['name']}")
    print(f"  date_from: {result['date_from']}")
    print(f"  date_to: {result['date_to']}")
else:
    print("NO DATA!")

session.close()
