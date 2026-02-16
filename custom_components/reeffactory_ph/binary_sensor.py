"""Binary sensor platform for Reef Factory pH Meter."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up pH alarm binary sensors."""
    coordinator: ReeffactoryCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ReeffactoryPhAlarmLow(coordinator),
            ReeffactoryPhAlarmHigh(coordinator),
        ]
    )


class ReeffactoryPhAlarmLow(BinarySensorEntity):
    """Binary sensor: pH is below alarm low threshold."""

    _attr_has_entity_name = True
    _attr_name = "pH Alarm Low"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_alarm_low"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self._coordinator.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DATA_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        data = self._coordinator.data
        if data:
            self._attr_is_on = data.current_ph <= data.alarm_low
            self._attr_extra_state_attributes = {
                "alarm_threshold": data.alarm_low,
            }
            self.async_write_ha_state()


class ReeffactoryPhAlarmHigh(BinarySensorEntity):
    """Binary sensor: pH is above alarm high threshold."""

    _attr_has_entity_name = True
    _attr_name = "pH Alarm High"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_alarm_high"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self._coordinator.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DATA_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        data = self._coordinator.data
        if data:
            self._attr_is_on = data.current_ph >= data.alarm_high
            self._attr_extra_state_attributes = {
                "alarm_threshold": data.alarm_high,
            }
            self.async_write_ha_state()
