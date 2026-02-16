"""Binary protocol encoder/decoder for Reef Factory devices.

Wire format (both directions):
    [serialNumber\\0][command\\0][subcommand\\0][identifier\\0][payload_bytes]

All string fields are ASCII, null-terminated. Payload is raw binary.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

PH_SCALE = 10000


@dataclass
class ReeffactoryMessage:
    """Parsed incoming WebSocket message."""

    serial_number: str
    command: str
    subcommand: str
    identifier: str
    payload: bytes


@dataclass
class PhSettings:
    """Parsed pH settings from device."""

    current_ph: float
    alarm_low: float
    alarm_high: float
    sound_enabled: bool
    adjustment: float | None = None


def parse_message(data: bytes) -> ReeffactoryMessage:
    """Parse a binary WebSocket frame into its string fields + payload."""
    pos = 0
    fields: list[str] = []
    for _ in range(4):
        chars: list[str] = []
        while pos < len(data):
            byte = data[pos]
            pos += 1
            if byte == 0:
                break
            chars.append(chr(byte))
        fields.append("".join(chars))

    return ReeffactoryMessage(
        serial_number=fields[0],
        command=fields[1],
        subcommand=fields[2],
        identifier=fields[3],
        payload=data[pos:],
    )


def parse_ph_settings(payload: bytes, firmware_version: str = "0.0.0") -> PhSettings:
    """Decode the binary payload from a pmRefresh/settings message.

    Layout:
        Bytes 0-3:   current pH * 10000 (big-endian uint32)
        Byte  4:     reserved
        Bytes 5-8:   alarm low * 10000
        Bytes 9-12:  alarm high * 10000
        Byte  13:    reserved
        Byte  14:    sound (0=off, 1=on)
        Bytes 15-18: adjustment * 10000 (signed, firmware >= 1.1.0)
    """
    scale = 1.0 / PH_SCALE
    offset = 0

    current_raw = struct.unpack_from(">I", payload, offset)[0]
    offset += 4
    offset += 1  # reserved

    alarm_low_raw = struct.unpack_from(">I", payload, offset)[0]
    offset += 4

    alarm_high_raw = struct.unpack_from(">I", payload, offset)[0]
    offset += 4
    offset += 1  # reserved

    sound = payload[offset]
    offset += 1

    adjustment = None
    if firmware_version >= "1.1.0" and len(payload) >= offset + 4:
        adj_raw = struct.unpack_from(">i", payload, offset)[0]  # signed
        adjustment = round(adj_raw * scale, 4)

    return PhSettings(
        current_ph=round(current_raw * scale, 2),
        alarm_low=round(alarm_low_raw * scale, 2),
        alarm_high=round(alarm_high_raw * scale, 2),
        sound_enabled=sound != 0,
        adjustment=adjustment,
    )


def parse_config_response(payload: bytes) -> dict[str, str]:
    """Extract serial number and firmware version from a refresh/config payload.

    Layout:
        Null-terminated serial number string
        1 byte language
        1 byte onboarding
        5 bytes firmware version string (e.g. "1.0.1")
    """
    pos = 0
    serial_chars: list[str] = []
    while pos < len(payload):
        b = payload[pos]
        pos += 1
        if b == 0:
            break
        serial_chars.append(chr(b))
    serial = "".join(serial_chars)

    pos += 1  # language byte
    pos += 1  # onboarding byte

    fw_chars: list[str] = []
    for _ in range(5):
        if pos < len(payload):
            fw_chars.append(chr(payload[pos]))
            pos += 1
    firmware = "".join(fw_chars)

    return {
        "serial_number": serial,
        "firmware_version": firmware,
    }


def build_message(
    serial_number: str,
    command: str,
    subcommand: str = "",
    identifier: str = "",
    payload: bytes | None = None,
) -> bytes:
    """Construct an outgoing binary WebSocket frame."""
    parts = bytearray()
    for field in (serial_number, command, subcommand, identifier):
        parts.extend(field.encode("ascii"))
        parts.append(0)
    if payload:
        parts.extend(payload)
    return bytes(parts)


def encode_ph_value(ph: float) -> bytes:
    """Encode a pH float as 4-byte big-endian integer (pH * 10000)."""
    return struct.pack(">I", int(round(ph * PH_SCALE)))
