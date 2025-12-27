"""Test the Azimut Energy MQTT client."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.azimut_energy.mqtt_client import AzimutMQTTClient


@pytest.fixture
def mqtt_client() -> AzimutMQTTClient:
    """Create a test MQTT client."""
    return AzimutMQTTClient(
        host="192.168.1.100",
        port=8883,
        serial="ABC123",
        use_tls=True,
    )


async def test_client_initialization(mqtt_client: AzimutMQTTClient) -> None:
    """Test client initialization."""
    assert mqtt_client.host == "192.168.1.100"
    assert mqtt_client.port == 8883
    assert mqtt_client.serial == "ABC123"
    assert mqtt_client.use_tls is True
    assert not mqtt_client.is_connected


async def test_connect_success(mqtt_client: AzimutMQTTClient) -> None:
    """Test successful connection."""
    mock_aiomqtt_client = MagicMock()
    mock_aiomqtt_client.__aenter__ = AsyncMock(return_value=mock_aiomqtt_client)
    mock_aiomqtt_client.__aexit__ = AsyncMock(return_value=None)
    mock_aiomqtt_client.subscribe = AsyncMock()

    with patch("custom_components.azimut_energy.mqtt_client.aiomqtt.Client") as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        result = await mqtt_client.connect()

    assert result is True
    assert mqtt_client.is_connected
    assert mock_aiomqtt_client.subscribe.call_count == 2  # Discovery + state topics


async def test_connect_failure(mqtt_client: AzimutMQTTClient) -> None:
    """Test connection failure."""
    with patch(
        "custom_components.azimut_energy.mqtt_client.aiomqtt.Client"
    ) as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        result = await mqtt_client.connect()

    assert result is False
    assert not mqtt_client.is_connected


async def test_disconnect(mqtt_client: AzimutMQTTClient) -> None:
    """Test disconnection."""
    mock_aiomqtt_client = MagicMock()
    mock_aiomqtt_client.__aenter__ = AsyncMock(return_value=mock_aiomqtt_client)
    mock_aiomqtt_client.__aexit__ = AsyncMock(return_value=None)
    mock_aiomqtt_client.subscribe = AsyncMock()

    with patch("custom_components.azimut_energy.mqtt_client.aiomqtt.Client") as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        await mqtt_client.connect()
        assert mqtt_client.is_connected

        await mqtt_client.disconnect()

    assert not mqtt_client.is_connected


async def test_discovery_callback(mqtt_client: AzimutMQTTClient) -> None:
    """Test discovery message callback."""
    received_payloads = []

    def discovery_callback(payload: dict) -> None:
        received_payloads.append(payload)

    mqtt_client.set_discovery_callback(discovery_callback)

    # Simulate discovery message handling
    discovery_payload = json.dumps(
        {
            "unique_id": "azen_ABC123_battery_soc",
            "name": "Battery SOC",
            "state_topic": "azen/ABC123/sensor/battery_soc/state",
        }
    )

    mqtt_client._handle_discovery_message(discovery_payload)

    assert len(received_payloads) == 1
    assert received_payloads[0]["unique_id"] == "azen_ABC123_battery_soc"


async def test_discovery_double_encoded_json(mqtt_client: AzimutMQTTClient) -> None:
    """Test handling of double-encoded JSON in discovery messages."""
    received_payloads = []

    def discovery_callback(payload: dict) -> None:
        received_payloads.append(payload)

    mqtt_client.set_discovery_callback(discovery_callback)

    # Double-encoded JSON (string inside JSON)
    inner_payload = {"unique_id": "test", "name": "Test Sensor"}
    double_encoded = json.dumps(json.dumps(inner_payload))

    mqtt_client._handle_discovery_message(double_encoded)

    assert len(received_payloads) == 1
    assert received_payloads[0]["unique_id"] == "test"


async def test_state_callback(mqtt_client: AzimutMQTTClient) -> None:
    """Test state message callback."""
    received_states = []

    def state_callback(topic: str, value: float) -> None:
        received_states.append((topic, value))

    mqtt_client.set_state_callback(state_callback)

    # Simulate state message handling
    mqtt_client._handle_state_message(
        "azen/ABC123/sensor/battery_soc/state", "85.50"
    )

    assert len(received_states) == 1
    assert received_states[0] == ("azen/ABC123/sensor/battery_soc/state", 85.50)


async def test_state_json_encoded_value(mqtt_client: AzimutMQTTClient) -> None:
    """Test handling of JSON-encoded state values."""
    received_states = []

    def state_callback(topic: str, value: float) -> None:
        received_states.append((topic, value))

    mqtt_client.set_state_callback(state_callback)

    # JSON-encoded string value (e.g., "344.00")
    mqtt_client._handle_state_message(
        "azen/ABC123/sensor/grid_power/state", '"1523.45"'
    )

    assert len(received_states) == 1
    assert received_states[0][1] == 1523.45


async def test_state_invalid_value(mqtt_client: AzimutMQTTClient) -> None:
    """Test handling of invalid state values."""
    received_states = []

    def state_callback(topic: str, value: float) -> None:
        received_states.append((topic, value))

    mqtt_client.set_state_callback(state_callback)

    # Invalid value should be ignored
    mqtt_client._handle_state_message(
        "azen/ABC123/sensor/battery_soc/state", "not_a_number"
    )

    assert len(received_states) == 0


async def test_connection_callback(mqtt_client: AzimutMQTTClient) -> None:
    """Test connection state callback."""
    connection_states = []

    def connection_callback(connected: bool) -> None:
        connection_states.append(connected)

    mqtt_client.set_connection_callback(connection_callback)

    mock_aiomqtt_client = MagicMock()
    mock_aiomqtt_client.__aenter__ = AsyncMock(return_value=mock_aiomqtt_client)
    mock_aiomqtt_client.__aexit__ = AsyncMock(return_value=None)
    mock_aiomqtt_client.subscribe = AsyncMock()

    with patch("custom_components.azimut_energy.mqtt_client.aiomqtt.Client") as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        await mqtt_client.connect()

    assert connection_states == [True]


async def test_topic_patterns(mqtt_client: AzimutMQTTClient) -> None:
    """Test topic pattern matching."""
    # Discovery topic pattern
    assert mqtt_client._discovery_pattern.match(
        "homeassistant/sensor/azen_ABC123/battery_soc/config"
    )
    assert not mqtt_client._discovery_pattern.match(
        "homeassistant/sensor/azen_OTHER/battery_soc/config"
    )

    # State topic pattern
    assert mqtt_client._state_pattern.match(
        "azen/ABC123/sensor/battery_soc/state"
    )
    assert not mqtt_client._state_pattern.match(
        "azen/OTHER/sensor/battery_soc/state"
    )


async def test_tls_context_creation(mqtt_client: AzimutMQTTClient) -> None:
    """Test TLS context is created when use_tls is True."""
    tls_context = mqtt_client._create_tls_context()

    assert tls_context is not None
    # Verify insecure settings (no cert verification)
    import ssl

    assert tls_context.verify_mode == ssl.CERT_NONE
    assert tls_context.check_hostname is False


async def test_no_tls_context() -> None:
    """Test no TLS context when use_tls is False."""
    client = AzimutMQTTClient(
        host="192.168.1.100",
        port=1883,
        serial="ABC123",
        use_tls=False,
    )

    tls_context = client._create_tls_context()
    assert tls_context is None

