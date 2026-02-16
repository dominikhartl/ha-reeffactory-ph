"""WebSocket connection manager for Reef Factory pH meter."""

from __future__ import annotations

import asyncio
import logging
import struct

import aiohttp

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    PH_SCALE_FACTOR,
    PING_INTERVAL,
    PONG_TIMEOUT,
    SIGNAL_CONNECTION_STATE,
    SIGNAL_DATA_UPDATED,
    WS_PATH,
    WS_SUBPROTOCOL,
)
from .protocol import (
    PhSettings,
    build_message,
    parse_config_response,
    parse_message,
    parse_ph_settings,
)

_LOGGER = logging.getLogger(__name__)


class ReeffactoryCoordinator:
    """Manages the persistent WebSocket connection to a Reef Factory pH device."""

    def __init__(self, hass: HomeAssistant, host: str, name: str) -> None:
        self.hass = hass
        self.host = host
        self.name = name
        self.serial_number: str | None = None
        self.firmware_version: str = "0.0.0"
        self.data: PhSettings | None = None
        self.available: bool = False

        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._listen_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._pong_received = asyncio.Event()
        self._retry_count = 0

    @property
    def unique_id_prefix(self) -> str:
        """Return a stable unique ID prefix for entities."""
        return self.serial_number or self.host

    @property
    def device_info(self) -> dict:
        """Return device info for the HA device registry."""
        return {
            "identifiers": {(DOMAIN, self.unique_id_prefix)},
            "name": self.name,
            "manufacturer": "Reef Factory",
            "model": "pH Meter",
            "sw_version": self.firmware_version,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Start the WebSocket connection."""
        self._stop_event.clear()
        await self._connect()

    async def async_stop(self) -> None:
        """Disconnect and clean up all resources."""
        self._stop_event.set()
        for task in (self._listen_task, self._ping_task):
            if task and not task.done():
                task.cancel()
        if self._ws and not self._ws.closed and self.serial_number:
            try:
                leave_payload = self.serial_number.encode("ascii") + b"\x00"
                msg = build_message(
                    self.serial_number, "pmConnect", "leave", payload=leave_payload
                )
                await self._ws.send_bytes(msg)
            except Exception:  # noqa: BLE001
                pass
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def _connect(self) -> None:
        """Establish a WebSocket connection to the device."""
        if self._stop_event.is_set():
            return
        url = f"ws://{self.host}/{WS_PATH}"
        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(
                url, protocols=[WS_SUBPROTOCOL]
            )
            self._retry_count = 0
            _LOGGER.debug("Connected to %s", url)

            # Request device config (serial number + firmware version)
            msg = build_message("0000000000000000", "get", "config")
            await self._ws.send_bytes(msg)

            self._listen_task = asyncio.create_task(self._listen())
            self._ping_task = asyncio.create_task(self._ping_loop())

        except (aiohttp.ClientError, OSError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Connection to %s failed: %s", self.host, err)
            if self._session and not self._session.closed:
                await self._session.close()
            await self._schedule_reconnect()

    async def _listen(self) -> None:
        """Read incoming WebSocket messages until disconnection."""
        try:
            async for ws_msg in self._ws:  # type: ignore[union-attr]
                if ws_msg.type == aiohttp.WSMsgType.BINARY:
                    self._handle_message(ws_msg.data)
                elif ws_msg.type in (
                    aiohttp.WSMsgType.ERROR,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                ):
                    break
        except asyncio.CancelledError:
            return
        except Exception:
            _LOGGER.exception("WebSocket listener error for %s", self.host)
        finally:
            if not self._stop_event.is_set():
                self._set_unavailable()
                await self._cleanup_and_reconnect()

    def _set_unavailable(self) -> None:
        """Mark the device as unavailable and notify entities."""
        if self.available:
            self.available = False
            async_dispatcher_send(self.hass, SIGNAL_CONNECTION_STATE, False)

    async def _cleanup_and_reconnect(self) -> None:
        """Close current session and schedule reconnect."""
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()
        await self._schedule_reconnect()

    async def _schedule_reconnect(self) -> None:
        """Reconnect with progressive back-off."""
        if self._stop_event.is_set():
            return
        self._retry_count += 1
        if self._retry_count <= 5:
            delay = 0.5
        elif self._retry_count <= 10:
            delay = 1.0
        else:
            delay = 2.0
        _LOGGER.debug(
            "Reconnecting to %s in %ss (attempt %d)",
            self.host,
            delay,
            self._retry_count,
        )
        await asyncio.sleep(delay)
        if not self._stop_event.is_set():
            await self._connect()

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    @callback
    def _handle_message(self, data: bytes) -> None:
        """Parse and dispatch an incoming binary message."""
        msg = parse_message(data)

        if msg.command == "refresh" and msg.subcommand == "config":
            self._handle_config(msg.payload)
        elif msg.command == "pmRefresh" and msg.subcommand == "settings":
            self._handle_ph_settings(msg.payload)
        elif msg.command == "pong":
            self._pong_received.set()

    def _handle_config(self, payload: bytes) -> None:
        """Process the config response to get serial number and firmware."""
        config = parse_config_response(payload)
        self.serial_number = config["serial_number"]
        self.firmware_version = config["firmware_version"]
        self.available = True
        _LOGGER.info(
            "Reef Factory device %s, firmware %s",
            self.serial_number,
            self.firmware_version,
        )
        async_dispatcher_send(self.hass, SIGNAL_CONNECTION_STATE, True)
        self.hass.async_create_task(self._subscribe())

    async def _subscribe(self) -> None:
        """Send pmConnect/join to start receiving pH data."""
        if not self._ws or self._ws.closed or not self.serial_number:
            return
        join_payload = self.serial_number.encode("ascii") + b"\x00"
        msg = build_message(
            self.serial_number, "pmConnect", "join", payload=join_payload
        )
        await self._ws.send_bytes(msg)

    def _handle_ph_settings(self, payload: bytes) -> None:
        """Decode pH data and notify sensor entities."""
        self.data = parse_ph_settings(payload, self.firmware_version)
        async_dispatcher_send(self.hass, SIGNAL_DATA_UPDATED)

    # ------------------------------------------------------------------
    # Ping / pong
    # ------------------------------------------------------------------

    async def _ping_loop(self) -> None:
        """Send periodic pings and verify pong responses."""
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(PING_INTERVAL)
                if not self._ws or self._ws.closed:
                    break
                self._pong_received.clear()
                serial = self.serial_number or "0000000000000000"
                msg = build_message(serial, "ping", "ping")
                try:
                    await self._ws.send_bytes(msg)
                except Exception:
                    break
                try:
                    await asyncio.wait_for(
                        self._pong_received.wait(), timeout=PONG_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning("Pong timeout from %s", self.host)
                    if self._ws and not self._ws.closed:
                        await self._ws.close()
                    break
        except asyncio.CancelledError:
            return

    # ------------------------------------------------------------------
    # Device commands
    # ------------------------------------------------------------------

    async def _send_command(
        self,
        command: str,
        subcommand: str,
        payload: bytes | None = None,
    ) -> None:
        """Send a command to the device."""
        if not self._ws or self._ws.closed or not self.serial_number:
            raise ConnectionError("Not connected to device")
        msg = build_message(self.serial_number, command, subcommand, payload=payload)
        await self._ws.send_bytes(msg)

    async def async_calibration_start(self) -> None:
        """Begin a calibration cycle."""
        await self._send_command("pmSet", "calibrationStart")

    async def async_calibration_low(self) -> None:
        """Confirm pH 4 (low-point) calibration."""
        await self._send_command("pmSet", "calibrationLow")

    async def async_calibration_high(self) -> None:
        """Confirm pH 7 (high-point) calibration."""
        await self._send_command("pmSet", "calibrationHigh")

    async def async_calibration_stop(self) -> None:
        """Cancel an in-progress calibration."""
        await self._send_command("pmSet", "calibrationStop")

    async def async_set_sound(self, enabled: bool) -> None:
        """Turn device alarm sound on or off."""
        await self._send_command("pmSound", "on" if enabled else "off")

    async def async_set_alarm_thresholds(
        self, alarm_low: float, alarm_high: float
    ) -> None:
        """Update alarm pH thresholds on the device."""
        payload = bytearray(17)
        struct.pack_into(">I", payload, 0, int(round(alarm_low * PH_SCALE_FACTOR)))
        struct.pack_into(">I", payload, 4, int(round(alarm_high * PH_SCALE_FACTOR)))
        await self._send_command("pmSet", "settings", bytes(payload))

    async def async_adjust_ph(self, value: float) -> None:
        """Apply a pH measurement adjustment/offset."""
        from .protocol import encode_ph_value

        await self._send_command("pmSet", "adjust", encode_ph_value(value))
