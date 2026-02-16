"""Sensor platform for Reef Factory pH Meter."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DATA_UPDATED
from .coordinator import ReeffactoryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up pH sensor entities."""
    coordinator: ReeffactoryCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ReeffactoryPhSensor(coordinator),
            ReeffactoryPhAdjustmentSensor(coordinator),
        ]
    )


class ReeffactoryPhSensor(SensorEntity):
    """Current pH measurement sensor."""

    _attr_has_entity_name = True
    _attr_name = "pH"
    _attr_native_unit_of_measurement = "pH"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_ph"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True if the device is connected."""
        return self._coordinator.available

    async def async_added_to_hass(self) -> None:
        """Subscribe to data updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DATA_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Update state from coordinator data."""
        if self._coordinator.data:
            self._attr_native_value = self._coordinator.data.current_ph
            self.async_write_ha_state()


class ReeffactoryPhAdjustmentSensor(SensorEntity):
    """pH adjustment/offset sensor (read-only, disabled by default)."""

    _attr_has_entity_name = True
    _attr_name = "pH Adjustment"
    _attr_native_unit_of_measurement = "pH"
    _attr_icon = "mdi:tune"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_ph_adjustment"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True if the device is connected."""
        return self._coordinator.available

    async def async_added_to_hass(self) -> None:
        """Subscribe to data updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DATA_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Update state from coordinator data."""
        if self._coordinator.data and self._coordinator.data.adjustment is not None:
            self._attr_native_value = self._coordinator.data.adjustment
            self.async_write_ha_state()
