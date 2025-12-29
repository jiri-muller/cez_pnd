"""The ČEZ Distribuce PND integration using requests."""
from __future__ import annotations

import asyncio
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

        _LOGGER.info("Writing historical power measurements to statistics")

        # Process consumption power measurements
        consumption_power_data = coordinator.data.get("consumption_power", {})
        measurements = consumption_power_data.get("measurements", [])
        if measurements:
            # Find actual entity_id from entity registry
            entity_id = hass.states.async_entity_ids("sensor")
            consumption_entity = next((e for e in entity_id if "consumption_power" in e.lower()), None)
            if consumption_entity:
                _LOGGER.debug(f"Found consumption power entity: {consumption_entity}")
                await async_write_power_history(hass, consumption_entity, measurements)
            else:
                _LOGGER.warning("Could not find consumption_power entity")

        # Process production power measurements
        production_power_data = coordinator.data.get("production_power", {})
        measurements = production_power_data.get("measurements", [])
        if measurements:
            # Find actual entity_id from entity registry
            entity_id = hass.states.async_entity_ids("sensor")
            production_entity = next((e for e in entity_id if "production_power" in e.lower()), None)
            if production_entity:
                _LOGGER.debug(f"Found production power entity: {production_entity}")
                await async_write_power_history(hass, production_entity, measurements)
            else:
                _LOGGER.warning("Could not find production_power entity")

    coordinator.async_add_listener(lambda: hass.async_create_task(async_write_historical_states()))

    # Perform one-time backfill of historical data if this is first setup
    backfill_done_key = f"{entry.entry_id}_backfill_done"
    if not hass.data[DOMAIN].get(backfill_done_key, False):
        _LOGGER.info("🔄 Starting one-time historical data backfill (30 days)")

        async def async_backfill():
            """Backfill historical power data."""
            try:
                # Fetch 30 days of historical data
                historical_data = await hass.async_add_executor_job(api.get_historical_data, 30)

                # Write historical data for consumption
                consumption_data = historical_data.get("consumption_power", {})
                if consumption_data.get("measurements"):
                    entity_id = hass.states.async_entity_ids("sensor")
                    consumption_entity = next((e for e in entity_id if "consumption_power" in e.lower()), None)
                    if consumption_entity:
                        await async_write_power_history(hass, consumption_entity, consumption_data["measurements"])

                # Write historical data for production
                production_data = historical_data.get("production_power", {})
                if production_data.get("measurements"):
                    entity_id = hass.states.async_entity_ids("sensor")
                    production_entity = next((e for e in entity_id if "production_power" in e.lower()), None)
                    if production_entity:
                        await async_write_power_history(hass, production_entity, production_data["measurements"])

                # Mark backfill as done
                hass.data[DOMAIN][backfill_done_key] = True
                _LOGGER.info("✅ Historical data backfill completed successfully")

            except Exception as err:
                _LOGGER.error(f"Failed to backfill historical data: {err}")

        # Run backfill in background after a short delay (let sensors initialize first)
        async def delayed_backfill():
            await asyncio.sleep(10)  # Wait 10 seconds for sensors to be ready
            await async_backfill()

        hass.async_create_task(delayed_backfill())

    return True


async def async_write_power_history(hass: HomeAssistant, entity_id: str, measurements: list[dict]) -> None:
    """Write historical power measurements as statistics."""
    if not measurements:
        _LOGGER.warning(f"No measurements to write for {entity_id}")
        return

    _LOGGER.info(f"📊 Processing {len(measurements)} historical measurements for {entity_id}")

    # Create statistic ID for external statistics (format: domain:unique_part)
    # Remove "sensor." prefix and use format compatible with external statistics
    unique_part = entity_id.replace("sensor.", "").replace("cez_pnd_", "")
    statistic_id = f"{DOMAIN}:{unique_part}"

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

    _LOGGER.info(f"📝 Individual measurements being added to statistics:")

    for idx, measurement in enumerate(measurements, 1):
        timestamp_str = measurement.get("timestamp", "")
        value = measurement.get("value", 0.0)

        if not timestamp_str:
            _LOGGER.warning(f"❌ Measurement #{idx}: No timestamp, skipping")
            continue

        try:
            # Parse timestamp (format: "29.12.2025 04:30")
            # Handle special case: 24:00 means midnight of next day
            if " 24:00" in timestamp_str:
                timestamp_str = timestamp_str.replace(" 24:00", " 00:00")
                timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M")
                # Add one day since 24:00 is midnight of next day
                timestamp = timestamp + timedelta(days=1)
            else:
                timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M")

            # Make timezone aware and convert to UTC
            timestamp_utc = dt_util.as_utc(dt_util.as_local(timestamp))

            # Create statistic data point
            stat = StatisticData(
                start=timestamp_utc,
                mean=value,  # Average power during this 15-min interval
                state=value,  # Current value at this timestamp
            )
            statistics.append(stat)

            # Log each individual measurement being added
            _LOGGER.info(
                f"  ✅ #{idx:2d}: {timestamp_str} → {value:6.3f} kW (UTC: {timestamp_utc.isoformat()})"
            )

        except (ValueError, TypeError) as err:
            _LOGGER.error(f"❌ Measurement #{idx}: Failed to parse timestamp '{timestamp_str}': {err}")
            continue

    if statistics:
        # Import statistics into recorder (this WILL show in statistics graphs)
        _LOGGER.info(f"💾 Importing {len(statistics)} statistics to recorder for {statistic_id}")
        async_add_external_statistics(hass, metadata, statistics)
        _LOGGER.info(
            f"✅ Successfully imported {len(statistics)} historical statistics for {statistic_id}"
        )
        _LOGGER.info(
            f"📅 Time range: {measurements[0]['timestamp']} → {measurements[-1]['timestamp']}"
        )
        _LOGGER.info(
            f"⚡ Power range: {min(m['value'] for m in measurements):.3f} - {max(m['value'] for m in measurements):.3f} kW"
        )
    else:
        _LOGGER.warning(f"⚠️  No valid statistics created for {statistic_id}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Close the API session
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        await hass.async_add_executor_job(api.close)
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
