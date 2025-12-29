"""API client for ČEZ Distribuce PND using requests library."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests
from bs4 import BeautifulSoup

from .const import (
    API_BASE_URL,
    API_DATA_URL,
    ID_ASSEMBLY_CONSUMPTION,
    ID_ASSEMBLY_PRODUCTION,
    ID_ASSEMBLY_CONSUMPTION_POWER,
    ID_ASSEMBLY_PRODUCTION_POWER,
)

_LOGGER = logging.getLogger(__name__)

# Version identifier for debugging
API_VERSION = "v1.5.0"
_LOGGER.info("ČEZ PND API version: %s", API_VERSION)


class CezPndApi:
    """API client for ČEZ Distribuce PND using requests.Session()."""

    def __init__(
        self,
        username: str,
        password: str,
        device_id: str,
    ) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.device_id = device_id
        # Use requests.Session for reliable cookie handling
        self.session = requests.Session()
        self.session.max_redirects = 10
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with the PND portal."""
        try:
            _LOGGER.info("🔐 Starting authentication (API version: %s)", API_VERSION)

            # Step 1: Get the OAuth2 authorization URL to be redirected to CAS login
            _LOGGER.debug("Starting OAuth2 flow")
            response = self.session.get(
                f"{API_BASE_URL}/oauth2/authorization/mepas-external",
                allow_redirects=True,
            )

            service_url = response.url
            _LOGGER.debug("CAS Login URL: %s", service_url)

            # Extract execution token from the form using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            execution_input = soup.find('input', {'name': 'execution'})

            if not execution_input:
                _LOGGER.error("Failed to extract execution token from login form")
                return False

            execution = execution_input['value']
            _LOGGER.debug("Extracted execution token (length: %d)", len(execution))

            # Step 2: Perform login with username and password
            login_data = {
                "username": self.username,
                "password": self.password,
                "execution": execution,
                "_eventId": "submit",
                "geolocation": "",
            }

            _LOGGER.debug("Attempting login to CAS")
            response = self.session.post(
                service_url,
                data=login_data,
                allow_redirects=True,
            )

            _LOGGER.debug("Login response status: %s", response.status_code)
            _LOGGER.debug("Login response URL: %s", response.url)

            # Check if redirected to ČEZ domain (successful login)
            final_url = str(response.url).lower()
            if "cezdistribuce.cz" not in final_url:
                _LOGGER.error("Unexpected redirect after login: %s", response.url)
                return False

            _LOGGER.debug("Login successful, redirected to: %s", response.url)
            _LOGGER.debug("Session has %d cookies", len(self.session.cookies))

            # Step 3: Access PND portal dashboard to establish session
            _LOGGER.debug("Accessing PND portal dashboard")
            response = self.session.get(
                f"{API_BASE_URL}/external/dashboard/view",
                allow_redirects=True,
            )

            _LOGGER.debug("Dashboard response status: %s", response.status_code)
            _LOGGER.info("✅ Authentication successful (API version: %s)", API_VERSION)
            self._authenticated = True
            return True

        except requests.RequestException as err:
            _LOGGER.error(
                "Network error during authentication: %s (type: %s)",
                err,
                type(err).__name__,
            )
            return False
        except Exception as err:
            _LOGGER.error(
                "Authentication error: %s (type: %s)",
                err,
                type(err).__name__,
            )
            return False

    def get_data(self) -> dict[str, Any]:
        """Fetch data from the PND portal."""
        # Ensure we're authenticated first
        if not self._authenticated:
            _LOGGER.debug("Not authenticated, authenticating...")
            if not self.authenticate():
                raise Exception("Authentication failed")

        now = datetime.now()
        date_format = "%d.%m.%Y %H:%M"

        # Get today's data
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_from = today.strftime(date_format)
        today_to = now.replace(hour=23, minute=59, second=59).strftime(date_format)

        # Get yesterday's data
        yesterday = today - timedelta(days=1)
        yesterday_from = yesterday.strftime(date_format)
        yesterday_to = yesterday.replace(hour=23, minute=59, second=59).strftime(date_format)

        _LOGGER.debug("Fetching today's data from %s to %s", today_from, today_to)
        _LOGGER.debug("Fetching yesterday's data from %s to %s", yesterday_from, yesterday_to)

        # Fetch today's data
        consumption_today = self._fetch_data(ID_ASSEMBLY_CONSUMPTION, today_from, today_to)
        production_today = self._fetch_data(ID_ASSEMBLY_PRODUCTION, today_from, today_to)

        # Fetch yesterday's data
        consumption_yesterday = self._fetch_data(ID_ASSEMBLY_CONSUMPTION, yesterday_from, yesterday_to)
        production_yesterday = self._fetch_data(ID_ASSEMBLY_PRODUCTION, yesterday_from, yesterday_to)

        # Fetch today's 15-minute power data (from midnight to now)
        consumption_power = self._fetch_power_data(ID_ASSEMBLY_CONSUMPTION_POWER, today_from, today_to)
        production_power = self._fetch_power_data(ID_ASSEMBLY_PRODUCTION_POWER, today_from, today_to)

        result = {
            "consumption_today": consumption_today,
            "consumption_yesterday": consumption_yesterday,
            "production_today": production_today,
            "production_yesterday": production_yesterday,
            "consumption_power": consumption_power,
            "production_power": production_power,
            "last_update": datetime.now().isoformat(),
        }

        _LOGGER.info(
            "Data fetched: today cons=%s prod=%s, yesterday cons=%s prod=%s, power cons=%s prod=%s",
            consumption_today.get("total", "N/A"),
            production_today.get("total", "N/A"),
            consumption_yesterday.get("total", "N/A"),
            production_yesterday.get("total", "N/A"),
            consumption_power.get("current", "N/A"),
            production_power.get("current", "N/A"),
        )

        return result

    def get_historical_data(self, days_back: int = 30) -> dict[str, Any]:
        """Fetch historical power data for backfill (multiple days)."""
        # Ensure we're authenticated first
        if not self._authenticated:
            _LOGGER.debug("Not authenticated, authenticating...")
            if not self.authenticate():
                raise Exception("Authentication failed")

        now = datetime.now()
        date_format = "%d.%m.%Y %H:%M"

        # Calculate date range (going back N days)
        end_date = now - timedelta(days=1)  # Yesterday (today's data may be incomplete)
        start_date = end_date - timedelta(days=days_back - 1)

        _LOGGER.info(
            f"🔄 Backfilling historical power data from {start_date.strftime('%d.%m.%Y')} "
            f"to {end_date.strftime('%d.%m.%Y')} ({days_back} days)"
        )

        # Fetch historical power data for the entire period
        interval_from = start_date.replace(hour=0, minute=0, second=0).strftime(date_format)
        interval_to = end_date.replace(hour=23, minute=59, second=59).strftime(date_format)

        consumption_power = self._fetch_power_data(
            ID_ASSEMBLY_CONSUMPTION_POWER,
            interval_from,
            interval_to,
        )
        production_power = self._fetch_power_data(
            ID_ASSEMBLY_PRODUCTION_POWER,
            interval_from,
            interval_to,
        )

        _LOGGER.info(
            f"✅ Backfill complete: consumption {len(consumption_power.get('measurements', []))} points, "
            f"production {len(production_power.get('measurements', []))} points"
        )

        return {
            "consumption_power": consumption_power,
            "production_power": production_power,
            "backfill_start": start_date.isoformat(),
            "backfill_end": end_date.isoformat(),
            "last_update": datetime.now().isoformat(),
        }

    def _fetch_data(
        self,
        id_assembly: int,
        interval_from: str,
        interval_to: str,
    ) -> dict[str, Any]:
        """Fetch data for a specific assembly ID."""
        payload = {
            "format": "chart",
            "idAssembly": id_assembly,
            "idDeviceSet": self.device_id,
            "intervalFrom": interval_from,
            "intervalTo": interval_to,
            "compareFrom": "",
            "opmId": None,
            "electrometerId": None,
        }

        try:
            _LOGGER.debug("Fetching data for assembly %s", id_assembly)
            response = self.session.post(
                API_DATA_URL,
                json=payload,
                allow_redirects=False,
            )

            _LOGGER.debug("Response status: %s, URL: %s", response.status_code, response.url)

            if response.status_code == 302 or response.status_code == 401:
                # Session expired, re-authenticate
                _LOGGER.info("Session expired, re-authenticating")
                self._authenticated = False
                if not self.authenticate():
                    raise Exception("Re-authentication failed")

                # Retry the request
                _LOGGER.debug("Retrying data fetch after re-authentication")
                response = self.session.post(
                    API_DATA_URL,
                    json=payload,
                    allow_redirects=False,
                )

            response.raise_for_status()
            data = response.json()

            _LOGGER.debug("Received data successfully")

            # Extract the relevant information
            if data.get("hasData") and data.get("series"):
                series = data["series"][0]
                stats = data["seriesStats"][0] if data.get("seriesStats") else {}

                # Extract the last data point value
                last_value = 0.0
                if series.get("data") and len(series["data"]) > 0:
                    last_data_point = series["data"][-1]
                    if len(last_data_point) >= 2:
                        last_value = float(last_data_point[1])

                return {
                    "value": last_value,
                    "total": self._parse_czech_number(stats.get("total", "0")),
                    "min": self._parse_czech_number(stats.get("min", "0")),
                    "max": self._parse_czech_number(stats.get("max", "0")),
                    "name": series.get("name", ""),
                    "unit": data.get("unitY", "kWh"),
                    "date_from": stats.get("dateFrom", ""),
                    "date_to": stats.get("dateTo", ""),
                }

            return {
                "value": 0.0,
                "total": 0.0,
                "min": 0.0,
                "max": 0.0,
                "name": "",
                "unit": "kWh",
                "date_from": "",
                "date_to": "",
            }

        except requests.RequestException as err:
            _LOGGER.error(
                "Network error fetching data for assembly %s: %s (type: %s)",
                id_assembly,
                err,
                type(err).__name__,
            )
            raise
        except Exception as err:
            _LOGGER.error(
                "Error fetching data for assembly %s: %s (type: %s)",
                id_assembly,
                err,
                type(err).__name__,
            )
            raise

    def _fetch_power_data(
        self,
        id_assembly: int,
        interval_from: str,
        interval_to: str,
    ) -> dict[str, Any]:
        """Fetch 15-minute power data for a specific assembly ID."""
        payload = {
            "format": "chart",
            "idAssembly": id_assembly,
            "idDeviceSet": self.device_id,
            "intervalFrom": interval_from,
            "intervalTo": interval_to,
            "compareFrom": None,
            "opmId": None,
            "electrometerId": None,
        }

        try:
            _LOGGER.debug("Fetching power data for assembly %s", id_assembly)
            response = self.session.post(
                API_DATA_URL,
                json=payload,
                allow_redirects=False,
            )

            _LOGGER.debug("Response status: %s, URL: %s", response.status_code, response.url)

            if response.status_code == 302 or response.status_code == 401:
                # Session expired, re-authenticate
                _LOGGER.info("Session expired, re-authenticating")
                self._authenticated = False
                if not self.authenticate():
                    raise Exception("Re-authentication failed")

                # Retry the request
                _LOGGER.debug("Retrying power data fetch after re-authentication")
                response = self.session.post(
                    API_DATA_URL,
                    json=payload,
                    allow_redirects=False,
                )

            response.raise_for_status()
            data = response.json()

            _LOGGER.debug("Received power data successfully")

            # Extract 15-minute interval data
            if data.get("hasData") and data.get("series"):
                series = data["series"][0]
                stats = data["seriesStats"][0] if data.get("seriesStats") else {}
                raw_data = series.get("data", [])

                # Filter out invalid data points (status != "naměřená data OK")
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

                return {
                    "current": current_power,
                    "latest_timestamp": latest_timestamp,
                    "measurements": valid_data,
                    "total": self._parse_czech_number(stats.get("total", "0")),
                    "min": self._parse_czech_number(stats.get("min", "0")),
                    "max": self._parse_czech_number(stats.get("max", "0")),
                    "name": series.get("name", ""),
                    "unit": data.get("unitY", "kW"),
                    "date_from": stats.get("dateFrom", ""),
                    "date_to": stats.get("dateTo", ""),
                }

            return {
                "current": 0.0,
                "latest_timestamp": "",
                "measurements": [],
                "total": 0.0,
                "min": 0.0,
                "max": 0.0,
                "name": "",
                "unit": "kW",
                "date_from": "",
                "date_to": "",
            }

        except requests.RequestException as err:
            _LOGGER.error(
                "Network error fetching power data for assembly %s: %s (type: %s)",
                id_assembly,
                err,
                type(err).__name__,
            )
            raise
        except Exception as err:
            _LOGGER.error(
                "Error fetching power data for assembly %s: %s (type: %s)",
                id_assembly,
                err,
                type(err).__name__,
            )
            raise

    @staticmethod
    def _parse_czech_number(value: str) -> float:
        """Parse Czech number format (comma as decimal separator)."""
        if isinstance(value, (int, float)):
            return float(value)
        try:
            # Replace comma with dot and remove spaces
            cleaned = str(value).replace(",", ".").replace(" ", "")
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0

    def close(self) -> None:
        """Close the requests session."""
        if self.session:
            self.session.close()
            _LOGGER.debug("Closed requests session")
