"""MQTT client for Azen Energy integration."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import ssl
from typing import Any, Callable

import aiomqtt

from .const import (
    DEFAULT_EXPIRE_AFTER,
    MQTT_KEEPALIVE,
    get_discovery_topic,
    get_state_topic,
)

_LOGGER = logging.getLogger(__name__)


class AzenMQTTClient:
    """MQTT client for Azen Energy System."""

    def __init__(
        self,
        host: str,
        port: int = 1883,
        serial: str = "",
        use_tls: bool = False,
    ) -> None:
        """Initialize the MQTT client."""
        self.host = host
        self.port = port
        self.serial = serial
        self.use_tls = use_tls

        self._client: aiomqtt.Client | None = None
        self._running = False
        self._connected = False

        # Callbacks for discovery and state messages
        self._discovery_callback: Callable[[dict[str, Any]], None] | None = None
        self._state_callback: Callable[[str, float], None] | None = None

        # Topic patterns
        self._discovery_topic = get_discovery_topic(serial)
        self._state_topic = get_state_topic(serial)

        # Regex patterns for parsing topics
        # Discovery: homeassistant/sensor/azen_{serial}/{sensor_id}/config
        self._discovery_pattern = re.compile(
            rf"homeassistant/sensor/azen_{re.escape(serial)}/([^/]+)/config"
        )
        # State: azen/{serial}/sensor/{sensor_id}/state
        self._state_pattern = re.compile(
            rf"azen/{re.escape(serial)}/sensor/([^/]+)/state"
        )

    def set_discovery_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Set callback for discovery messages."""
        self._discovery_callback = callback

    def set_state_callback(
        self, callback: Callable[[str, float], None]
    ) -> None:
        """Set callback for state messages.
        
        Callback receives (state_topic, value).
        """
        self._state_callback = callback

    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            # Configure TLS if enabled
            tls_context = None
            if self.use_tls:
                tls_context = ssl.create_default_context()
                tls_context.check_hostname = False
                tls_context.verify_mode = ssl.CERT_NONE

            # Create client
            self._client = aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                tls_context=tls_context,
                identifier=f"ha_azen_{self.serial}",
                keepalive=MQTT_KEEPALIVE,
            )

            await self._client.__aenter__()
            self._connected = True

            # Subscribe to discovery and state topics
            await self._client.subscribe(self._discovery_topic)
            await self._client.subscribe(self._state_topic)

            _LOGGER.info(
                "Connected to MQTT broker at %s:%s for device %s",
                self.host,
                self.port,
                self.serial,
            )
            _LOGGER.debug("Subscribed to discovery topic: %s", self._discovery_topic)
            _LOGGER.debug("Subscribed to state topic: %s", self._state_topic)

            return True

        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._running = False
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as err:
                _LOGGER.debug("Error during MQTT disconnect: %s", err)
            finally:
                self._client = None
                self._connected = False

    async def listen(self) -> None:
        """Listen for MQTT messages."""
        if not self._client:
            raise RuntimeError("Not connected to MQTT broker")

        self._running = True

        try:
            async for message in self._client.messages:
                if not self._running:
                    break

                topic = str(message.topic)
                payload = message.payload.decode()

                try:
                    # Check if this is a discovery message
                    discovery_match = self._discovery_pattern.match(topic)
                    if discovery_match:
                        self._handle_discovery_message(payload)
                        continue

                    # Check if this is a state message
                    state_match = self._state_pattern.match(topic)
                    if state_match:
                        self._handle_state_message(topic, payload)
                        continue

                    _LOGGER.debug("Unhandled topic: %s", topic)

                except Exception as err:
                    _LOGGER.error("Error processing MQTT message on %s: %s", topic, err)

        except asyncio.CancelledError:
            _LOGGER.debug("MQTT listen task cancelled")
        except Exception as err:
            _LOGGER.error("Error in MQTT listen loop: %s", err)
            raise

    def _handle_discovery_message(self, payload: str) -> None:
        """Handle a discovery message (JSON payload)."""
        try:
            data = json.loads(payload)
            _LOGGER.debug("Received discovery message: %s", data)

            if self._discovery_callback:
                self._discovery_callback(data)

        except json.JSONDecodeError as err:
            _LOGGER.warning("Failed to decode discovery JSON: %s", err)

    def _handle_state_message(self, topic: str, payload: str) -> None:
        """Handle a state message (plain numeric string)."""
        try:
            # State payloads are plain numeric strings like "1234.56"
            value = float(payload)
            _LOGGER.debug("Received state update on %s: %s", topic, value)

            if self._state_callback:
                self._state_callback(topic, value)

        except ValueError as err:
            _LOGGER.warning("Failed to parse state value '%s': %s", payload, err)

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected
