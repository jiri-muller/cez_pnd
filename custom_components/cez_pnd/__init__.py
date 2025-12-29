"""The ČEZ Distribuce PND integration using requests."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    StatisticMetaData,
    StatisticData,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api_requests import CezPndApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

UPDATE_INTERVAL = timedelta(hours=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ČEZ Distribuce PND from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    device_id = entry.data.get("device_id", "")

    api = CezPndApi(username, password, device_id)

    async def async_update_data():
        """Fetch data from API running in executor."""
        try:
            # Run synchronous API call in executor
            return await hass.async_add_executor_job(api.get_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add listener to write historical states after each update
    async def async_write_historical_states():
        """Write historical states for 15-minute power measurements."""
        if not coordinator.data:
            return

        # Process consumption power measurements
        consumption_power_data = coordinator.data.get("consumption_power", {})
        measurements = consumption_power_data.get("measurements", [])
        if measurements:
            entity_id = f"sensor.cez_pnd_consumption_power"
            await async_write_power_history(hass, entity_id, measurements)

        # Process production power measurements
        production_power_data = coordinator.data.get("production_power", {})
        measurements = production_power_data.get("measurements", [])
        if measurements:
            entity_id = f"sensor.cez_pnd_production_power"
            await async_write_power_history(hass, entity_id, measurements)

    coordinator.async_add_listener(lambda: hass.async_create_task(async_write_historical_states()))

    return True


async def async_write_power_history(hass: HomeAssistant, entity_id: str, measurements: list[dict]) -> None:
    """Write historical power measurements as statistics."""
    if not measurements:
        return

    _LOGGER.debug(f"Writing {len(measurements)} historical statistics for {entity_id}")

    # Create statistic ID (using the entity_id with : instead of .)
    statistic_id = entity_id

    # Define metadata for the statistics
    metadata = StatisticMetaData(
        has_mean=True,
        has_sum=False,
        name=entity_id.replace("sensor.cez_pnd_", "ČEZ PND ").replace("_", " ").title(),
        source=DOMAIN,
        statistic_id=statistic_id,
        unit_of_measurement=UnitOfPower.KILO_WATT,
    )

    # Convert measurements to statistics
    statistics = []
    for measurement in measurements:
        timestamp_str = measurement.get("timestamp", "")
        value = measurement.get("value", 0.0)

        if not timestamp_str:
            continue

        try:
            # Parse timestamp (format: "29.12.2025 04:30")
            timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M")
            # Make timezone aware and convert to UTC
            timestamp = dt_util.as_utc(dt_util.as_local(timestamp))

            # Create statistic data point
            stat = StatisticData(
                start=timestamp,
                mean=value,  # Average power during this 15-min interval
                state=value,  # Current value at this timestamp
            )
            statistics.append(stat)

        except (ValueError, TypeError) as err:
            _LOGGER.warning(f"Failed to parse timestamp '{timestamp_str}': {err}")
            continue

    if statistics:
        # Import statistics into recorder
        async_add_external_statistics(hass, metadata, statistics)
        _LOGGER.info(f"Imported {len(statistics)} historical statistics for {statistic_id}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Close the API session
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        await hass.async_add_executor_job(api.close)
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
