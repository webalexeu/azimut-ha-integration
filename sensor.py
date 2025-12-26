"""Sensor platform for the Azen Energy integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_SERIAL, DEFAULT_EXPIRE_AFTER, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Map string device classes to SensorDeviceClass enum
DEVICE_CLASS_MAP = {
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "voltage": SensorDeviceClass.VOLTAGE,
    "battery": SensorDeviceClass.BATTERY,
    "current": SensorDeviceClass.CURRENT,
    "temperature": SensorDeviceClass.TEMPERATURE,
}

# Map string state classes to SensorStateClass enum
STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
    "total": SensorStateClass.TOTAL,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Azen sensors from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get(CONF_SERIAL, "")

    # Track created sensors by unique_id to avoid duplicates
    created_sensors: dict[str, AzenSensor] = {}

    @callback
    def handle_discovery(payload: dict[str, Any]) -> None:
        """Handle discovery message and create sensor."""
        unique_id = payload.get("unique_id")
        if not unique_id:
            _LOGGER.warning("Discovery payload missing unique_id: %s", payload)
            return

        # Skip if sensor already exists
        if unique_id in created_sensors:
            _LOGGER.debug("Sensor %s already exists, skipping", unique_id)
            return

        # Create the sensor entity
        sensor = AzenSensor(
            coordinator=coordinator,
            payload=payload,
            serial=serial,
        )
        created_sensors[unique_id] = sensor

        # Add the entity
        async_add_entities([sensor])
        _LOGGER.info("Created sensor: %s", unique_id)

    @callback
    def handle_state_update(state_topic: str, value: float) -> None:
        """Handle state update and route to correct sensor."""
        for sensor in created_sensors.values():
            if sensor.state_topic == state_topic:
                sensor.update_value(value)
                return

        _LOGGER.debug("No sensor found for state topic: %s", state_topic)

    # Register callbacks with coordinator
    coordinator.set_discovery_callback(handle_discovery)
    coordinator.set_state_callback(handle_state_update)


class AzenSensor(SensorEntity):
    """Azen sensor entity created from MQTT discovery."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        payload: dict[str, Any],
        serial: str,
    ) -> None:
        """Initialize the sensor from discovery payload."""
        self._coordinator = coordinator
        self._serial = serial

        # Extract fields from discovery payload
        self._attr_unique_id = payload.get("unique_id", "")
        self._attr_name = payload.get("name", "Unknown Sensor")
        self._state_topic = payload.get("state_topic", "")
        self._attr_native_unit_of_measurement = payload.get("unit_of_measurement")
        self._attr_icon = payload.get("icon")

        # Map device class string to enum
        device_class_str = payload.get("device_class")
        if device_class_str and device_class_str in DEVICE_CLASS_MAP:
            self._attr_device_class = DEVICE_CLASS_MAP[device_class_str]

        # Map state class string to enum
        state_class_str = payload.get("state_class")
        if state_class_str and state_class_str in STATE_CLASS_MAP:
            self._attr_state_class = STATE_CLASS_MAP[state_class_str]

        # Expiration for availability
        self._expire_after = payload.get("expire_after", DEFAULT_EXPIRE_AFTER)
        self._last_update: datetime | None = None
        self._unsub_expire_check: Any = None

        # Device info from payload
        device_info = payload.get("device", {})
        identifiers = device_info.get("identifiers", [])
        if identifiers:
            # Convert list to set of tuples for HA
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, identifiers[0]) if isinstance(identifiers[0], str) else identifiers[0]},
                name=device_info.get("name", f"Azen {serial}"),
                manufacturer=device_info.get("manufacturer", "Azimut"),
                model=device_info.get("model", "Azen Energy System"),
                sw_version=device_info.get("sw_version"),
            )

        # Initial state
        self._attr_native_value: float | None = None
        self._attr_available = False

    @property
    def state_topic(self) -> str:
        """Return the state topic for this sensor."""
        return self._state_topic

    @callback
    def update_value(self, value: float) -> None:
        """Update the sensor value from MQTT state message."""
        self._attr_native_value = value
        self._attr_available = True
        self._last_update = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Set up periodic check for expiration
        if self._expire_after > 0:
            self._unsub_expire_check = async_track_time_interval(
                self.hass,
                self._check_expiration,
                timedelta(seconds=min(self._expire_after / 2, 60)),
            )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity is being removed."""
        await super().async_will_remove_from_hass()

        if self._unsub_expire_check:
            self._unsub_expire_check()
            self._unsub_expire_check = None

    @callback
    def _check_expiration(self, now: datetime) -> None:
        """Check if sensor has expired."""
        if self._last_update is None:
            return

        if (now - self._last_update).total_seconds() > self._expire_after:
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()
                _LOGGER.debug(
                    "Sensor %s became unavailable (no update for %s seconds)",
                    self._attr_unique_id,
                    self._expire_after,
                )
