"""Sensor platform for ČEZ Distribuce PND integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

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
        CezPndSensor(
            coordinator,
            config_entry,
            "consumption_today",
            "Consumption Today",
            "mdi:transmission-tower",
        ),
        CezPndSensor(
            coordinator,
            config_entry,
            "consumption_yesterday",
            "Consumption Yesterday",
            "mdi:transmission-tower",
        ),
        CezPndSensor(
            coordinator,
            config_entry,
            "production_today",
            "Production Today",
            "mdi:solar-power",
        ),
        CezPndSensor(
            coordinator,
            config_entry,
            "production_yesterday",
            "Production Yesterday",
            "mdi:solar-power",
        ),
    ]

    async_add_entities(sensors)


class CezPndSensor(CoordinatorEntity, SensorEntity):
    """Representation of a ČEZ PND sensor."""

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
