"""API client for ČEZ Distribuce PND."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BASE_URL,
    API_DATA_URL,
    ID_ASSEMBLY_CONSUMPTION,
    ID_ASSEMBLY_PRODUCTION,
)

_LOGGER = logging.getLogger(__name__)


class CezPndApi:
    """API client for ČEZ Distribuce PND."""

    def __init__(
        self,
        username: str,
        password: str,
        device_id: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.device_id = device_id
        self.hass = hass
        self.session: ClientSession = async_get_clientsession(hass)
        self._cookies: dict[str, Any] = {}

    async def async_authenticate(self) -> bool:
        """Authenticate with the PND portal."""
        try:
            import re

            # Step 1: Get the OAuth2 authorization URL to be redirected to CAS login
            _LOGGER.debug("Starting OAuth2 flow")
            async with self.session.get(
                f"{API_BASE_URL}/oauth2/authorization/mepas-external",
                allow_redirects=True,
            ) as response:
                service_url = str(response.url)
                html = await response.text()
                _LOGGER.debug("CAS Login URL: %s", service_url)

                # Extract execution token from the form
                execution_match = re.search(r'name="execution"\s+value="([^"]+)"', html)
                execution = execution_match.group(1) if execution_match else None

                if not execution:
                    _LOGGER.error("Failed to extract execution token from login form")
                    return False

                _LOGGER.debug("Extracted execution token (length: %d)", len(execution))

            # Step 2: Perform login with username and password
            login_data = {
                "username": self.username,
                "password": self.password,
                "execution": execution,
                "_eventId": "submit",
                "geolocation": "",
            }

            # Set proper headers for form submission
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": service_url,
                "Origin": "https://cas.cez.cz",
            }

            _LOGGER.debug("Attempting login to CAS")
            async with self.session.post(
                service_url,
                data=login_data,
                headers=headers,
                allow_redirects=True,
            ) as response:
                _LOGGER.debug("Login response status: %s", response.status)
                _LOGGER.debug("Login response URL: %s", response.url)

                # Check if we're still on login page (authentication failed)
                if "login" in str(response.url).lower() and response.status != 200:
                    _LOGGER.error("Login failed with status %s", response.status)
                    return False

                # Check if redirected back to PND (successful login)
                if "pnd.cezdistribuce.cz" not in str(response.url).lower():
                    _LOGGER.error("Unexpected redirect after login: %s", response.url)
                    return False

                # Store cookies for subsequent requests
                self._cookies = {cookie.key: cookie.value for cookie in self.session.cookie_jar}
                _LOGGER.debug("Stored %d cookies", len(self._cookies))

            # Step 3: Verify authentication by trying to access the dashboard
            async with self.session.get(
                f"{API_BASE_URL}/external/dashboard/view",
                allow_redirects=True,
            ) as response:
                if "login" in str(response.url).lower():
                    _LOGGER.error("Authentication failed - redirected to login")
                    return False

                _LOGGER.info("Authentication successful")
                return True

        except Exception as err:
            _LOGGER.error("Authentication error: %s", err)
            raise

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch data from the PND portal."""
        # Get yesterday's data (since today's data might not be available yet)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        # Format dates as required by the API
        date_format = "%d.%m.%Y %H:%M"
        interval_from = start_date.strftime(date_format).replace(" 00:00", " 00:00")
        interval_to = end_date.strftime(date_format).replace(" 00:00", " 00:00")

        _LOGGER.debug(
            "Fetching data from %s to %s",
            interval_from,
            interval_to,
        )

        # Fetch consumption data
        consumption_data = await self._fetch_data(
            ID_ASSEMBLY_CONSUMPTION,
            interval_from,
            interval_to,
        )

        # Fetch production data
        production_data = await self._fetch_data(
            ID_ASSEMBLY_PRODUCTION,
            interval_from,
            interval_to,
        )

        return {
            "consumption": consumption_data,
            "production": production_data,
            "last_update": datetime.now().isoformat(),
        }

    async def _fetch_data(
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
            async with self.session.post(
                API_DATA_URL,
                json=payload,
                allow_redirects=True,
            ) as response:
                if response.status == 401 or "login" in str(response.url).lower():
                    # Session expired, re-authenticate
                    _LOGGER.info("Session expired, re-authenticating")
                    await self.async_authenticate()

                    # Retry the request
                    async with self.session.post(
                        API_DATA_URL,
                        json=payload,
                    ) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json()

                response.raise_for_status()
                data = await response.json()

                _LOGGER.debug("Received data: %s", data)

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

        except Exception as err:
            _LOGGER.error("Error fetching data for assembly %s: %s", id_assembly, err)
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
