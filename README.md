# Reef Factory pH Meter - Home Assistant Integration

Home Assistant custom integration for [Reef Factory](https://reeffactory.com/) pH meters. Connects directly to the ESP32 device over your local network via WebSocket — no cloud required.

## Features

- **Real-time pH monitoring** — push-based updates, no polling
- **Calibration controls** — pH 4 and pH 7 two-point calibration from the HA UI
- **Alarm thresholds** — adjustable low/high pH alarm thresholds
- **Alarm sound control** — toggle the device buzzer on/off
- **Binary alarm sensors** — triggers when pH goes out of range
- **Auto-reconnect** — handles connection drops with progressive back-off

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three-dot menu (top right) → **Custom repositories**
3. Add `https://github.com/dominikhartl/ha-reeffactory-ph` with category **Integration**
4. Click **Download** on the Reef Factory pH Meter card
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/reeffactory_ph/` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Reef Factory pH Meter**
3. Enter the IP address of your device (e.g. `192.168.10.46`)
4. The integration will connect to the device and verify the connection

## Entities

Once configured, the following entities are created:

| Entity | Type | Description |
|--------|------|-------------|
| pH | Sensor | Current pH reading (updates in real-time) |
| pH Adjustment | Sensor | Calibration offset applied (disabled by default) |
| pH Alarm Low | Binary Sensor | On when pH is below the low threshold |
| pH Alarm High | Binary Sensor | On when pH is above the high threshold |
| Alarm pH Low | Number | Low alarm threshold (writable) |
| Alarm pH High | Number | High alarm threshold (writable) |
| Alarm Sound | Switch | Toggle the device alarm buzzer |
| Start Calibration pH 4 | Button | Begin pH 4 calibration |
| Confirm Calibration pH 4 | Button | Confirm pH 4 calibration after stabilization |
| Start Calibration pH 7 | Button | Begin pH 7 calibration |
| Confirm Calibration pH 7 | Button | Confirm pH 7 calibration after stabilization |
| Cancel Calibration | Button | Cancel an in-progress calibration |

## Calibration

The device uses a standard two-point calibration with pH 4 and pH 7 reference solutions.

### pH 4 Calibration

1. Place the probe in a **pH 4 buffer solution**
2. Press **Start Calibration pH 4**
3. Wait **60 seconds** for the reading to stabilize
4. Press **Confirm Calibration pH 4**

### pH 7 Calibration

1. Place the probe in a **pH 7 buffer solution**
2. Press **Start Calibration pH 7**
3. Wait **60 seconds** for the reading to stabilize
4. Press **Confirm Calibration pH 7**

Press **Cancel Calibration** at any time to abort.

## Technical Details

- Communicates via WebSocket at `ws://<device-ip>/controler`
- Uses a binary protocol with null-terminated string fields
- Push-based data delivery (`iot_class: local_push`) — no polling
- Heartbeat ping every 30 seconds with automatic reconnection
- No cloud dependencies, no external Python packages required
