"""Number platform for Reef Factory pH Meter alarm thresholds."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up alarm threshold number entities."""
    coordinator: ReeffactoryCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ReeffactoryAlarmLowNumber(coordinator),
            ReeffactoryAlarmHighNumber(coordinator),
        ]
    )


class ReeffactoryAlarmLowNumber(NumberEntity):
    """Number entity for the alarm low pH threshold."""

    _attr_has_entity_name = True
    _attr_name = "Alarm pH Low"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 14.0
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "pH"
    _attr_icon = "mdi:arrow-down-bold"

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_alarm_low_threshold"
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
        if self._coordinator.data:
            self._attr_native_value = self._coordinator.data.alarm_low
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Send updated alarm low threshold to the device."""
        alarm_high = (
            self._coordinator.data.alarm_high if self._coordinator.data else 8.5
        )
        await self._coordinator.async_set_alarm_thresholds(value, alarm_high)


class ReeffactoryAlarmHighNumber(NumberEntity):
    """Number entity for the alarm high pH threshold."""

    _attr_has_entity_name = True
    _attr_name = "Alarm pH High"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 14.0
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "pH"
    _attr_icon = "mdi:arrow-up-bold"

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_alarm_high_threshold"
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
        if self._coordinator.data:
            self._attr_native_value = self._coordinator.data.alarm_high
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Send updated alarm high threshold to the device."""
        alarm_low = (
            self._coordinator.data.alarm_low if self._coordinator.data else 7.5
        )
        await self._coordinator.async_set_alarm_thresholds(alarm_low, value)
