"""Test the Azen Energy integration."""
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.azen.const import CONF_SERIAL, DOMAIN


async def test_setup_entry_success(hass):
    """Test successful setup of config entry."""
    entry = AsyncMock()
    entry.data = {
        "host": "192.168.1.100",
        "port": 1883,
        CONF_SERIAL: "ABC123",
    }
    entry.entry_id = "test_entry"

    with patch(
        "custom_components.azen.mqtt_client.AzenMQTTClient.connect",
        return_value=True,
    ):
        from custom_components.azen import async_setup_entry

        result = await async_setup_entry(hass, entry)
        assert result is True


async def test_setup_entry_connection_failure(hass):
    """Test setup failure when MQTT connection fails."""
    entry = AsyncMock()
    entry.data = {
        "host": "192.168.1.100",
        "port": 1883,
        CONF_SERIAL: "ABC123",
    }
    entry.entry_id = "test_entry"

    with patch(
        "custom_components.azen.mqtt_client.AzenMQTTClient.connect",
        return_value=False,
    ):
        from custom_components.azen import async_setup_entry

        result = await async_setup_entry(hass, entry)
        assert result is False
