"""Test the Azimut Energy sensor platform."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN  # noqa: I001
from custom_components.azimut_energy.sensor import AzimutSensor  # noqa: I001


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Mock coordinator."""
    coordinator = MagicMock()
    coordinator.set_discovery_callback = MagicMock()
    coordinator.set_state_callback = MagicMock()
    coordinator.set_connection_callback = MagicMock()
    return coordinator


@pytest.fixture
def sample_discovery_payload() -> dict:
    """Sample discovery payload."""
    return {
        "unique_id": "azen_ABC123_battery_soc",
        "name": "Battery State of Charge",
        "state_topic": "azen/ABC123/sensor/battery_soc/state",
        "unit_of_measurement": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "icon": "mdi:battery",
        "expire_after": 300,
        "device": {
            "identifiers": ["azen_ABC123"],
            "name": "Azen ABC123",
            "manufacturer": "Azimut",
            "model": "Azen Energy System",
            "sw_version": "1.0.0",
        },
    }


async def test_sensor_creation_from_discovery(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor creation from discovery payload."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    # Capture the callbacks
    callbacks = {}

    def capture_discovery_cb(cb):
        callbacks["discovery"] = cb

    def capture_state_cb(cb):
        callbacks["state"] = cb

    def capture_connection_cb(cb):
        callbacks["connection"] = cb

    mock_coordinator.set_discovery_callback.side_effect = capture_discovery_cb
    mock_coordinator.set_state_callback.side_effect = capture_state_cb
    mock_coordinator.set_connection_callback.side_effect = capture_connection_cb

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Simulate discovery message
    callbacks["discovery"](sample_discovery_payload)

    # Verify sensor was created
    assert add_entities_mock.call_count == 1
    sensors = add_entities_mock.call_args[0][0]
    assert len(sensors) == 1

    sensor = sensors[0]
    assert sensor.unique_id == "azen_ABC123_battery_soc"
    assert sensor.name == "Battery State of Charge"
    assert sensor.state_topic == "azen/ABC123/sensor/battery_soc/state"


async def test_sensor_state_update(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor state update."""
    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=sample_discovery_payload,
        serial="ABC123",
    )
    sensor.hass = hass

    # Initial state should be None and unavailable
    assert sensor.native_value is None
    assert not sensor.available

    # Update value
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_value(85.5)

    # Verify state
    assert sensor.native_value == 85.5
    assert sensor.available


async def test_sensor_duplicate_discovery(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test that duplicate discovery messages don't create duplicate sensors."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: None
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Call discovery callback twice with same payload
    callbacks["discovery"](sample_discovery_payload)
    callbacks["discovery"](sample_discovery_payload)

    # Should only create one sensor
    assert add_entities_mock.call_count == 1


async def test_sensor_state_routing(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test state updates are routed to correct sensor."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: callbacks.update(
        {"state": cb}
    )
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Create sensor via discovery
    callbacks["discovery"](sample_discovery_payload)

    sensor = add_entities_mock.call_args[0][0][0]
    sensor.hass = hass

    # Mock async_write_ha_state
    with patch.object(sensor, "async_write_ha_state"):
        # Send state update
        callbacks["state"]("azen/ABC123/sensor/battery_soc/state", 92.0)

    assert sensor.native_value == 92.0


async def test_sensor_connection_availability(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor availability based on connection state."""
    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=sample_discovery_payload,
        serial="ABC123",
    )
    sensor.hass = hass

    # Set sensor as available
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_value(50.0)
    assert sensor.available

    # Simulate connection loss
    with patch.object(sensor, "async_write_ha_state"):
        sensor.set_connection_available(False)
    assert not sensor.available


async def test_sensor_expiration(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor expiration after no updates."""
    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=sample_discovery_payload,
        serial="ABC123",
    )
    sensor.hass = hass
    sensor._mqtt_connected = True

    # Set initial value
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_value(1000.0)
    assert sensor.available

    # Simulate time passing beyond expiration (300 seconds)
    sensor._last_update = dt_util.utcnow() - timedelta(seconds=301)

    with patch.object(sensor, "async_write_ha_state"):
        sensor._check_expiration(dt_util.utcnow())

    # Sensor should be unavailable
    assert not sensor.available


async def test_sensor_device_class_mapping(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test device class string to enum mapping."""
    from homeassistant.components.sensor import SensorDeviceClass

    payload = {
        "unique_id": "test_power",
        "name": "Test Power",
        "state_topic": "test/state",
        "device_class": "power",
        "device": {"identifiers": ["test"]},
    }

    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=payload,
        serial="TEST",
    )

    assert sensor.device_class == SensorDeviceClass.POWER


async def test_sensor_state_class_mapping(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test state class string to enum mapping."""
    from homeassistant.components.sensor import SensorStateClass

    payload = {
        "unique_id": "test_energy",
        "name": "Test Energy",
        "state_topic": "test/state",
        "state_class": "total_increasing",
        "device": {"identifiers": ["test"]},
    }

    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=payload,
        serial="TEST",
    )

    assert sensor.state_class == SensorStateClass.TOTAL_INCREASING


async def test_sensor_missing_unique_id(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test discovery payload without unique_id is ignored."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: None
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Discovery without unique_id
    callbacks["discovery"]({"name": "Test", "state_topic": "test"})

    # Should not create sensor
    assert add_entities_mock.call_count == 0

