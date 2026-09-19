"""Constants for Tuya ↔ Sonoff Climate Bridge."""

DOMAIN = "tuya_sonoff_climate_bridge"

CONF_ZONE_NAME = "zone_name"
CONF_THERMOSTAT = "thermostat"
CONF_VALVES = "valves"
CONF_FROST_TEMP = "frost_temperature"

DEFAULT_FROST_TEMP = 7.0

MODE_OFF = "off"
MODE_HEAT = "heat"

ATTR_TEMPERATURE = "temperature"
ATTR_HVAC_ACTION = "hvac_action"

TARGET_TOLERANCE = 0.05
EXPECTED_TIMEOUT = 20.0
SONOFF_HEAT_CONFIRM_TIMEOUT = 10.0
SONOFF_RESTORE_WAIT_TIMEOUT = 5.5
