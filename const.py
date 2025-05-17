"""Constants for the Azimut Battery integration."""

DOMAIN = "azimut_battery"

# Default API endpoint for battery data
API_ENDPOINT = "/api/battery/current"

# Default scan interval in seconds
DEFAULT_SCAN_INTERVAL = 30

# Unit of measurement
VOLT = "V"
AMPERE = "A"
WATT = "W"
PERCENTAGE = "%"
TEMP_CELSIUS = "°C"

# Icon mapping
ICON_BATTERY = "mdi:battery"
ICON_VOLTAGE = "mdi:flash"
ICON_CURRENT = "mdi:current-ac"
ICON_POWER = "mdi:power-plug"
ICON_TEMPERATURE = "mdi:thermometer"
ICON_EFFICIENCY = "mdi:flash-auto"
ICON_ENERGY = "mdi:lightning-bolt"

# Device class mapping (for Home Assistant)
DEVICE_CLASS_BATTERY = "battery"
DEVICE_CLASS_VOLTAGE = "voltage"
DEVICE_CLASS_CURRENT = "current"
DEVICE_CLASS_POWER = "power"
DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_ENERGY = "energy"

# State class for sensors
STATE_CLASS_MEASUREMENT = "measurement"
STATE_CLASS_TOTAL_INCREASING = "total_increasing"

# Attribute keys (updated to match new API structure)
ATTR_BATTERY_VOLTAGE = "dc_voltage"
ATTR_BATTERY_CURRENT = "dc_current"
ATTR_BATTERY_POWER = "dc_power"
ATTR_BATTERY_AC_POWER = "ac_power"
ATTR_BATTERY_EFFICIENCY = "ac_dc_efficiency"
ATTR_BATTERY_SOC = "soc"
ATTR_BATTERY_TEMPERATURE = "temperature"
ATTR_BATTERY_STATUS = "status"
ATTR_UPDATED_AT = "updated_at"
ATTR_ENERGY_TO_BATTERY = "energy_to_battery"
ATTR_ENERGY_FROM_BATTERY = "energy_from_battery" 