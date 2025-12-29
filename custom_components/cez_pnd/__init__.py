"""The ČEZ Distribuce PND integration using requests."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
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

    # Historical sensors automatically handle 15-minute data via homeassistant-historical-sensor
    # No need for separate statistics import since that requires hourly intervals

    # Perform one-time backfill of historical data if this is first setup
    backfill_done_key = f"{entry.entry_id}_backfill_done"
    if not hass.data[DOMAIN].get(backfill_done_key, False):
        _LOGGER.info("🔄 Starting one-time historical data backfill (30 days)")

        async def async_backfill():
            """Backfill historical power data to historical sensors."""
            try:
                # Fetch 30 days of historical data
                historical_data = await hass.async_add_executor_job(api.get_historical_data, 30)

                # Find the historical sensor entities
                consumption_hist_entity = None
                production_hist_entity = None

                for entity_id in hass.states.async_entity_ids("sensor"):
                    if "consumption_power_history" in entity_id.lower():
                        consumption_hist_entity = entity_id
                    elif "production_power_history" in entity_id.lower():
                        production_hist_entity = entity_id

                # Import HistoricalState if available
                try:
                    from homeassistant_historical_sensor import HistoricalState

                    # Process consumption power backfill
                    consumption_data = historical_data.get("consumption_power", {})
                    measurements = consumption_data.get("measurements", [])
                    if measurements and consumption_hist_entity:
                        _LOGGER.info(f"📊 Backfilling {len(measurements)} consumption measurements")
                        historical_states = []

                        for measurement in measurements:
                            timestamp_str = measurement.get("timestamp", "")
                            value = measurement.get("value", 0.0)

                            if not timestamp_str:
                                continue

                            try:
                                # Handle 24:00 timestamp
                                ts = timestamp_str
                                if " 24:00" in ts:
                                    ts = ts.replace(" 24:00", " 00:00")
                                    dt = datetime.strptime(ts, "%d.%m.%Y %H:%M")
                                    dt = dt + timedelta(days=1)
                                else:
                                    dt = datetime.strptime(ts, "%d.%m.%Y %H:%M")

                                dt = dt_util.as_local(dt)
                                hist_state = HistoricalState(state=value, dt=dt)
                                historical_states.append(hist_state)
                            except (ValueError, TypeError) as err:
                                _LOGGER.warning(f"Failed to parse timestamp '{timestamp_str}': {err}")
                                continue

                        # Get the sensor entity and update its historical states
                        entity = hass.data["entity_components"]["sensor"].get_entity(consumption_hist_entity)
                        if entity and hasattr(entity, "_attr_historical_states"):
                            entity._attr_historical_states = historical_states
                            entity.async_write_ha_state()
                            _LOGGER.info(f"✅ Backfilled {len(historical_states)} consumption states")

                    # Process production power backfill
                    production_data = historical_data.get("production_power", {})
                    measurements = production_data.get("measurements", [])
                    if measurements and production_hist_entity:
                        _LOGGER.info(f"📊 Backfilling {len(measurements)} production measurements")
                        historical_states = []

                        for measurement in measurements:
                            timestamp_str = measurement.get("timestamp", "")
                            value = measurement.get("value", 0.0)

                            if not timestamp_str:
                                continue

                            try:
                                # Handle 24:00 timestamp
                                ts = timestamp_str
                                if " 24:00" in ts:
                                    ts = ts.replace(" 24:00", " 00:00")
                                    dt = datetime.strptime(ts, "%d.%m.%Y %H:%M")
                                    dt = dt + timedelta(days=1)
                                else:
                                    dt = datetime.strptime(ts, "%d.%m.%Y %H:%M")

                                dt = dt_util.as_local(dt)
                                hist_state = HistoricalState(state=value, dt=dt)
                                historical_states.append(hist_state)
                            except (ValueError, TypeError) as err:
                                _LOGGER.warning(f"Failed to parse timestamp '{timestamp_str}': {err}")
                                continue

                        # Get the sensor entity and update its historical states
                        entity = hass.data["entity_components"]["sensor"].get_entity(production_hist_entity)
                        if entity and hasattr(entity, "_attr_historical_states"):
                            entity._attr_historical_states = historical_states
                            entity.async_write_ha_state()
                            _LOGGER.info(f"✅ Backfilled {len(historical_states)} production states")

                except ImportError:
                    _LOGGER.warning("homeassistant-historical-sensor not available, skipping backfill")

                # Mark backfill as done
                hass.data[DOMAIN][backfill_done_key] = True
                _LOGGER.info("✅ Historical data backfill completed successfully")

            except Exception as err:
                _LOGGER.error(f"Failed to backfill historical data: {err}", exc_info=True)

        # Run backfill in background after a short delay (let sensors initialize first)
        async def delayed_backfill():
            await asyncio.sleep(10)  # Wait 10 seconds for sensors to be ready
            await async_backfill()

        hass.async_create_task(delayed_backfill())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Close the API session
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        await hass.async_add_executor_job(api.close)
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
