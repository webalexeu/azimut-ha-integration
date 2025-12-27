"""MQTT client for Azimut Energy integration."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import ssl
from typing import Any, Callable

import aiomqtt

from .const import (
    MQTT_KEEPALIVE,
    MQTT_RECONNECT_INTERVAL,
    get_discovery_topic,
    get_state_topic,
)

_LOGGER = logging.getLogger(__name__)


class AzimutMQTTClient:
    """MQTT client for Azimut Energy System with automatic reconnection."""

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
        self._reconnect_task: asyncio.Task | None = None
        self._connection_lost_logged = False

        # Callbacks for discovery and state messages
        self._discovery_callback: Callable[[dict[str, Any]], None] | None = None
        self._state_callback: Callable[[str, float], None] | None = None
        self._connection_callback: Callable[[bool], None] | None = None

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

    def set_connection_callback(
        self, callback: Callable[[bool], None]
    ) -> None:
        """Set callback for connection state changes.

        Callback receives True when connected, False when disconnected.
        """
        self._connection_callback = callback

    def _create_tls_context(self) -> ssl.SSLContext | None:
        """Create TLS context if TLS is enabled."""
        if not self.use_tls:
            return None
        tls_context = ssl.create_default_context()
        tls_context.check_hostname = False
        tls_context.verify_mode = ssl.CERT_NONE
        return tls_context

    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self._client = aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                tls_context=self._create_tls_context(),
                identifier=f"ha_azen_{self.serial}",
                keepalive=MQTT_KEEPALIVE,
            )

            await self._client.__aenter__()
            self._connected = True
            self._connection_lost_logged = False

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

            # Notify connection callback
            if self._connection_callback:
                self._connection_callback(True)

            return True

        except Exception as err:
            if not self._connection_lost_logged:
                _LOGGER.error("Failed to connect to MQTT broker: %s", err)
                self._connection_lost_logged = True
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._running = False

        # Cancel reconnect task if running
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as err:
                _LOGGER.debug("Error during MQTT disconnect: %s", err)
            finally:
                self._client = None
                self._connected = False

    async def listen_with_reconnect(self) -> None:
        """Listen for MQTT messages with automatic reconnection."""
        self._running = True

        while self._running:
            try:
                if not self._connected:
                    if await self.connect():
                        _LOGGER.info("MQTT connection restored")
                    else:
                        # Wait before retry, but check if we should stop
                        for _ in range(MQTT_RECONNECT_INTERVAL):
                            if not self._running:
                                return
                            await asyncio.sleep(1)
                        continue

                # Listen for messages
                await self._listen_loop()

            except aiomqtt.MqttError as err:
                self._connected = False
                if self._connection_callback:
                    self._connection_callback(False)

                if not self._connection_lost_logged:
                    _LOGGER.warning(
                        "MQTT connection lost: %s. Reconnecting in %s seconds...",
                        err,
                        MQTT_RECONNECT_INTERVAL,
                    )
                    self._connection_lost_logged = True

                # Clean up old client
                if self._client:
                    try:
                        await self._client.__aexit__(None, None, None)
                    except Exception:
                        pass
                    self._client = None

                # Wait before reconnect
                for _ in range(MQTT_RECONNECT_INTERVAL):
                    if not self._running:
                        return
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                _LOGGER.debug("MQTT listen task cancelled")
                return

            except Exception as err:
                _LOGGER.error("Unexpected error in MQTT loop: %s", err)
                self._connected = False
                await asyncio.sleep(MQTT_RECONNECT_INTERVAL)

    async def _listen_loop(self) -> None:
        """Internal listen loop for MQTT messages."""
        if not self._client:
            raise RuntimeError("Not connected to MQTT broker")

        async for message in self._client.messages:
            if not self._running:
                break

            topic = str(message.topic)
            try:
                payload = message.payload.decode()
            except UnicodeDecodeError:
                _LOGGER.debug("Failed to decode payload on topic %s", topic)
                continue

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
                _LOGGER.debug("Error processing MQTT message on %s: %s", topic, err)

    def _handle_discovery_message(self, payload: str) -> None:
        """Handle a discovery message (JSON payload)."""
        try:
            data = json.loads(payload)

            # Handle double-encoded JSON (string inside JSON)
            if isinstance(data, str):
                data = json.loads(data)

            _LOGGER.debug("Received discovery message: %s", data)

            if self._discovery_callback and isinstance(data, dict):
                self._discovery_callback(data)

        except json.JSONDecodeError as err:
            _LOGGER.debug("Failed to decode discovery JSON: %s", err)

    def _handle_state_message(self, topic: str, payload: str) -> None:
        """Handle a state message (numeric string, possibly JSON-encoded)."""
        try:
            # Try to parse as JSON first (in case it's a quoted string like "344.00")
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, (int, float)):
                    value = float(parsed)
                elif isinstance(parsed, str):
                    value = float(parsed)
                else:
                    raise ValueError(f"Unexpected type: {type(parsed)}")
            except json.JSONDecodeError:
                # Not JSON, try direct float conversion
                value = float(payload)

            _LOGGER.debug("Received state update on %s: %s", topic, value)

            if self._state_callback:
                self._state_callback(topic, value)

        except ValueError as err:
            _LOGGER.debug("Failed to parse state value '%s': %s", payload, err)

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected

    # Keep old method for backwards compatibility
    async def listen(self) -> None:
        """Listen for MQTT messages (legacy method, use listen_with_reconnect)."""
        await self.listen_with_reconnect()
