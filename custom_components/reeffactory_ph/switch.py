"""Switch platform for Reef Factory pH Meter sound control."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up the sound switch entity."""
    coordinator: ReeffactoryCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReeffactorySoundSwitch(coordinator)])


class ReeffactorySoundSwitch(SwitchEntity):
    """Switch to control the device alarm sound."""

    _attr_has_entity_name = True
    _attr_name = "Alarm Sound"
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: ReeffactoryCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_sound"
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
            self._attr_is_on = self._coordinator.data.sound_enabled
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the alarm sound."""
        await self._coordinator.async_set_sound(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the alarm sound."""
        await self._coordinator.async_set_sound(False)
