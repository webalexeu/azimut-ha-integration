import asyncio
import logging
import json
import websockets

_LOGGER = logging.getLogger(__name__)


class WebSocketManager:
    """Manages a shared WebSocket connection."""

    def __init__(self, url):
        self._url = url
        self._connection = None
        self._listeners = []
        self._task = asyncio.create_task(self.connect_websocket())

    def add_listener(self, listener):
        """Add a listener for WebSocket messages."""
        self._listeners.append(listener)

    async def connect_websocket(self):
        """Connect to the WebSocket and listen for messages."""
        try:
            async with websockets.connect(self._url) as websocket:
                self._connection = websocket
                while True:
                    message = await websocket.recv()
                    _LOGGER.info("Received message: %s", message)
                    data = json.loads(message)
                    for listener in self._listeners:
                        listener(data)
        except Exception as e:
            _LOGGER.error("Error connecting to WebSocket: %s", e)
            self._connection = None

    async def close(self):
        """Close the WebSocket connection."""
        if self._connection:
            await self._connection.close()
