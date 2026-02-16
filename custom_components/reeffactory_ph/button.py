"""Button platform for Reef Factory pH Meter calibration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ReeffactoryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up calibration button entities."""
    coordinator: ReeffactoryCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ReeffactoryCalibrationButton(
                coordinator,
                key="start_cal_4",
                name="Start Calibration pH 4",
                icon="mdi:beaker-outline",
                action=coordinator.async_calibration_start,
            ),
            ReeffactoryCalibrationButton(
                coordinator,
                key="confirm_cal_4",
                name="Confirm Calibration pH 4",
                icon="mdi:check-circle-outline",
                action=coordinator.async_calibration_low,
            ),
            ReeffactoryCalibrationButton(
                coordinator,
                key="start_cal_7",
                name="Start Calibration pH 7",
                icon="mdi:beaker-outline",
                action=coordinator.async_calibration_start,
            ),
            ReeffactoryCalibrationButton(
                coordinator,
                key="confirm_cal_7",
                name="Confirm Calibration pH 7",
                icon="mdi:check-circle-outline",
                action=coordinator.async_calibration_high,
            ),
            ReeffactoryCalibrationButton(
                coordinator,
                key="cancel_cal",
                name="Cancel Calibration",
                icon="mdi:close-circle-outline",
                action=coordinator.async_calibration_stop,
            ),
        ]
    )


class ReeffactoryCalibrationButton(ButtonEntity):
    """A button entity that sends a calibration command to the device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ReeffactoryCoordinator,
        key: str,
        name: str,
        icon: str,
        action,
    ) -> None:
        self._coordinator = coordinator
        self._action = action
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self._coordinator.available

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._action()
