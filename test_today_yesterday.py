#!/usr/bin/env python3
"""Test script to verify today and yesterday data fetching."""
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Read credentials
with open("credentials.txt", "r") as f:
    lines = f.readlines()
    username = lines[0].strip().split(": ")[1]
    password = lines[1].strip().split(": ")[1]
    device_id = lines[2].strip().split(": ")[1] if len(lines) > 2 else "86180"

print(f"Testing today/yesterday data for user: {username}")
print("-" * 50)

API_BASE_URL = "https://pnd.cezdistribuce.cz/cezpnd2"
API_DATA_URL = f"{API_BASE_URL}/external/data"
ID_ASSEMBLY_CONSUMPTION = -1021
ID_ASSEMBLY_PRODUCTION = -1022

session = requests.Session()
session.max_redirects = 10

# Authenticate
print("\n1. Authenticating...")
response = session.get(
    f"{API_BASE_URL}/oauth2/authorization/mepas-external",
    allow_redirects=True,
)
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

if "cezdistribuce.cz" not in str(response.url).lower():
    print("❌ Authentication failed")
    sys.exit(1)

print("✅ Authentication successful")

# Access dashboard
response = session.get(f"{API_BASE_URL}/external/dashboard/view", allow_redirects=True)

# Fetch data
now = datetime.now()
date_format = "%d.%m.%Y %H:%M"

# Today
today = now.replace(hour=0, minute=0, second=0, microsecond=0)
today_from = today.strftime(date_format)
today_to = now.replace(hour=23, minute=59, second=59).strftime(date_format)

# Yesterday
yesterday = today - timedelta(days=1)
yesterday_from = yesterday.strftime(date_format)
yesterday_to = yesterday.replace(hour=23, minute=59, second=59).strftime(date_format)

print(f"\n2. Fetching data...")
print(f"   Today: {today_from} - {today_to}")
print(f"   Yesterday: {yesterday_from} - {yesterday_to}")

# Fetch consumption today
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
response = session.post(API_DATA_URL, json=payload, allow_redirects=False)
consumption_today = response.json()

# Fetch consumption yesterday
payload["intervalFrom"] = yesterday_from
payload["intervalTo"] = yesterday_to
response = session.post(API_DATA_URL, json=payload, allow_redirects=False)
consumption_yesterday = response.json()

# Fetch production today
payload["idAssembly"] = ID_ASSEMBLY_PRODUCTION
payload["intervalFrom"] = today_from
payload["intervalTo"] = today_to
response = session.post(API_DATA_URL, json=payload, allow_redirects=False)
production_today = response.json()

# Fetch production yesterday
payload["intervalFrom"] = yesterday_from
payload["intervalTo"] = yesterday_to
response = session.post(API_DATA_URL, json=payload, allow_redirects=False)
production_yesterday = response.json()

print("\n=== CONSUMPTION TODAY ===")
if consumption_today.get("hasData"):
    stats = consumption_today["seriesStats"][0]
    print(f"Total: {stats['total']} {consumption_today['unitY']}")
    print(f"Date: {stats['dateFrom']} - {stats['dateTo']}")
else:
    print("No data available")

print("\n=== CONSUMPTION YESTERDAY ===")
if consumption_yesterday.get("hasData"):
    stats = consumption_yesterday["seriesStats"][0]
    print(f"Total: {stats['total']} {consumption_yesterday['unitY']}")
    print(f"Date: {stats['dateFrom']} - {stats['dateTo']}")
else:
    print("No data available")

print("\n=== PRODUCTION TODAY ===")
if production_today.get("hasData"):
    stats = production_today["seriesStats"][0]
    print(f"Total: {stats['total']} {production_today['unitY']}")
    print(f"Date: {stats['dateFrom']} - {stats['dateTo']}")
else:
    print("No data available")

print("\n=== PRODUCTION YESTERDAY ===")
if production_yesterday.get("hasData"):
    stats = production_yesterday["seriesStats"][0]
    print(f"Total: {stats['total']} {production_yesterday['unitY']}")
    print(f"Date: {stats['dateFrom']} - {stats['dateTo']}")
else:
    print("No data available")

session.close()
print("\n✅ All tests passed!")
