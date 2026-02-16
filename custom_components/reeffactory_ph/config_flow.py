"""Config flow for Reef Factory pH Meter integration."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME

from .const import DOMAIN, WS_PATH, WS_SUBPROTOCOL
from .protocol import build_message, parse_config_response, parse_message

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Reef Factory pH Meter"


class ReeffactoryPhConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reef Factory pH Meter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step: manual IP entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                config = await self._async_get_device_config(host)
            except Exception:
                _LOGGER.exception("Failed to connect to %s", host)
                errors["base"] = "cannot_connect"
            else:
                serial = config["serial_number"]
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data={
                        CONF_HOST: host,
                        CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                        "serial_number": serial,
                        "firmware_version": config["firmware_version"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )

    async def _async_get_device_config(self, host: str) -> dict[str, str]:
        """Connect briefly to the device and retrieve its serial + firmware."""
        url = f"ws://{host}/{WS_PATH}"
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                url, protocols=[WS_SUBPROTOCOL], timeout=10
            ) as ws:
                msg = build_message("0000000000000000", "get", "config")
                await ws.send_bytes(msg)
                async with asyncio.timeout(10):
                    async for ws_msg in ws:
                        if ws_msg.type == aiohttp.WSMsgType.BINARY:
                            parsed = parse_message(ws_msg.data)
                            if (
                                parsed.command == "refresh"
                                and parsed.subcommand == "config"
                            ):
                                return parse_config_response(parsed.payload)
        raise ConnectionError("No config response from device")
