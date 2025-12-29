"""Sensor platform for ČEZ Distribuce PND integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

try:
    from homeassistant_historical_sensor import (
        HistoricalSensor,
        HistoricalState,
        PollUpdateMixin,
    )
    HISTORICAL_SENSOR_AVAILABLE = True
except ImportError:
    HISTORICAL_SENSOR_AVAILABLE = False
    _LOGGER.warning("homeassistant-historical-sensor not available, historical sensors disabled")

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ČEZ Distribuce PND sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    sensors = [
        CezPndEnergySensor(
            coordinator,
            config_entry,
            "consumption_today",
            "Consumption Today",
            "mdi:transmission-tower",
        ),
        CezPndEnergySensor(
            coordinator,
            config_entry,
            "consumption_yesterday",
            "Consumption Yesterday",
            "mdi:transmission-tower",
        ),
        CezPndEnergySensor(
            coordinator,
            config_entry,
            "production_today",
            "Production Today",
            "mdi:solar-power",
        ),
        CezPndEnergySensor(
            coordinator,
            config_entry,
            "production_yesterday",
            "Production Yesterday",
            "mdi:solar-power",
        ),
        CezPndPowerSensor(
            coordinator,
            config_entry,
            "consumption_power",
            "Consumption Power",
            "mdi:transmission-tower",
        ),
        CezPndPowerSensor(
            coordinator,
            config_entry,
            "production_power",
            "Production Power",
            "mdi:solar-power",
        ),
    ]

    # Add historical sensors if module is available
    if HISTORICAL_SENSOR_AVAILABLE:
        sensors.extend([
            CezPndHistoricalPowerSensor(
                coordinator,
                config_entry,
                "consumption_power",
                "Consumption Power History",
                "mdi:chart-line",
            ),
            CezPndHistoricalPowerSensor(
                coordinator,
                config_entry,
                "production_power",
                "Production Power History",
                "mdi:chart-line",
            ),
        ])
        _LOGGER.info("Historical sensors enabled for 15-minute power data")

    async_add_entities(sensors)


class CezPndEnergySensor(CoordinatorEntity, SensorEntity):
    """Representation of a ČEZ PND energy sensor (kWh)."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = f"ČEZ PND {name}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_icon = icon
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_suggested_display_precision = 2  # Show 2 decimal places (e.g., 14.39)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            _LOGGER.warning(f"Sensor {self._sensor_type}: coordinator.data is None")
            return None

        data = self.coordinator.data.get(self._sensor_type, {})
        if not data:
            _LOGGER.warning(f"Sensor {self._sensor_type}: No data in coordinator for this sensor type. Available keys: {list(self.coordinator.data.keys())}")

        total = data.get("total", 0.0)
        _LOGGER.debug(f"Sensor {self._sensor_type}: native_value = {total}")
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data is None:
            return {}

        data = self.coordinator.data.get(self._sensor_type, {})
        return {
            "last_value": data.get("value", 0.0),
            "min": data.get("min", 0.0),
            "max": data.get("max", 0.0),
            "meter_name": data.get("name", ""),
            "date_from": data.get("date_from", ""),
            "date_to": data.get("date_to", ""),
            "last_update": self.coordinator.data.get("last_update", ""),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._sensor_type in self.coordinator.data
        )

    @property
    def last_reset(self) -> datetime | None:
        """Return the time when the sensor was last reset (start of measurement period)."""
        if self.coordinator.data is None:
            return None

        data = self.coordinator.data.get(self._sensor_type, {})
        date_from_str = data.get("date_from", "")

        if not date_from_str:
            return None

        try:
            # Parse the date_from string (format: "28.12.2025")
            date_obj = datetime.strptime(date_from_str, "%d.%m.%Y")
            # Convert to timezone-aware datetime at midnight
            return dt_util.start_of_local_day(dt_util.as_local(date_obj))
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "Failed to parse date_from '%s' for sensor %s: %s",
                date_from_str,
                self._sensor_type,
                err,
            )
            return None


class CezPndPowerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a ČEZ PND power sensor (kW) - 15-minute intervals."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = f"ČEZ PND {name}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_icon = icon
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_suggested_display_precision = 3  # Show 3 decimal places (e.g., 0.959)

    @property
    def native_value(self) -> float | None:
        """Return the current power value (latest valid measurement)."""
        if self.coordinator.data is None:
            _LOGGER.warning(f"Sensor {self._sensor_type}: coordinator.data is None")
            return None

        data = self.coordinator.data.get(self._sensor_type, {})
        if not data:
            _LOGGER.warning(
                f"Sensor {self._sensor_type}: No data in coordinator. Available keys: {list(self.coordinator.data.keys())}"
            )
            return None

        current = data.get("current", 0.0)
        _LOGGER.debug(f"Sensor {self._sensor_type}: native_value = {current} kW")
        return current

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data is None:
            return {}

        data = self.coordinator.data.get(self._sensor_type, {})
        measurements = data.get("measurements", [])

        return {
            "latest_timestamp": data.get("latest_timestamp", ""),
            "min_today": data.get("min", 0.0),
            "max_today": data.get("max", 0.0),
            "total_energy_today": data.get("total", 0.0),
            "meter_name": data.get("name", ""),
            "date_from": data.get("date_from", ""),
            "date_to": data.get("date_to", ""),
            "measurement_count": len(measurements),
            "last_update": self.coordinator.data.get("last_update", ""),
            "unit": data.get("unit", "kW"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._sensor_type in self.coordinator.data
        )



# Historical sensor implementation (requires homeassistant-historical-sensor)
if HISTORICAL_SENSOR_AVAILABLE:
    class CezPndHistoricalPowerSensor(PollUpdateMixin, HistoricalSensor, CoordinatorEntity, SensorEntity):
        """Historical power sensor showing all 15-minute measurements in regular history graph."""

        def __init__(
            self,
            coordinator: DataUpdateCoordinator,
            config_entry: ConfigEntry,
            sensor_type: str,
            name: str,
            icon: str,
        ) -> None:
            """Initialize the historical sensor."""
            CoordinatorEntity.__init__(self, coordinator)
            self._sensor_type = sensor_type
            self._attr_name = f"ČEZ PND {name}"
            self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}_historical"
            self._attr_icon = icon
            self._attr_device_class = SensorDeviceClass.POWER
            # Note: No state_class - historical sensors dont use automatic statistics
            self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
            self._attr_suggested_display_precision = 3
            self._attr_historical_states = []

        async def async_update_historical(self) -> None:
            """Update historical states from coordinator data."""
            if self.coordinator.data is None:
                _LOGGER.debug(f"Historical sensor {self._sensor_type}: No coordinator data")
                return

            data = self.coordinator.data.get(self._sensor_type, {})
            measurements = data.get("measurements", [])

            if not measurements:
                _LOGGER.debug(f"Historical sensor {self._sensor_type}: No measurements")
                return

            _LOGGER.info(f"📊 Historical sensor {self._sensor_type}: Processing {len(measurements)} measurements")

            # Convert measurements to HistoricalState objects
            historical_states = []
            for measurement in measurements:
                timestamp_str = measurement.get("timestamp", "")
                value = measurement.get("value", 0.0)

                if not timestamp_str:
                    continue

                try:
                    # Parse timestamp (format: "29.12.2025 04:30")
                    dt = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M")
                    # Make timezone aware
                    dt = dt_util.as_local(dt)

                    # Create historical state
                    hist_state = HistoricalState(
                        state=value,
                        dt=dt,
                    )
                    historical_states.append(hist_state)

                except (ValueError, TypeError) as err:
                    _LOGGER.warning(f"Failed to parse timestamp \"{timestamp_str}\": {err}")
                    continue

            self._attr_historical_states = historical_states
            _LOGGER.info(
                f"✅ Historical sensor {self._sensor_type}: Prepared {len(historical_states)} states "
                f"from {measurements[0][\"timestamp\"]} to {measurements[-1][\"timestamp\"]}"
            )

        @property
        def extra_state_attributes(self) -> dict[str, Any]:
            """Return additional attributes."""
            if self.coordinator.data is None:
                return {}

            data = self.coordinator.data.get(self._sensor_type, {})
            measurements = data.get("measurements", [])

            return {
                "measurement_count": len(measurements),
                "date_from": data.get("date_from", ""),
                "date_to": data.get("date_to", ""),
                "meter_name": data.get("name", ""),
                "unit": data.get("unit", "kW"),
                "last_update": self.coordinator.data.get("last_update", ""),
            }

