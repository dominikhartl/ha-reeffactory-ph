"""Constants for the Reef Factory pH Meter integration."""

DOMAIN = "reeffactory_ph"
PLATFORMS = ["sensor", "binary_sensor", "number", "switch", "button"]

WS_PATH = "controler"
WS_SUBPROTOCOL = "arduino"

PING_INTERVAL = 30  # seconds
PONG_TIMEOUT = 10  # seconds

PH_SCALE_FACTOR = 10000

SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"
SIGNAL_CONNECTION_STATE = f"{DOMAIN}_connection_state"
