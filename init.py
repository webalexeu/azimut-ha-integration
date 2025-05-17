"""The Azimut Energy integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, API_ENDPOINT, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Azimut Battery Monitor from a config entry."""
    host = entry.data["host"]
    port = entry.data.get("port", 8080)
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    base_url = f"http://{host}:{port}"

    coordinator = AzimutBatteryDataCoordinator(
        hass,
        base_url=base_url,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms for this device/entry.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for config entry changes
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class AzimutBatteryDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching battery data."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        scan_interval: int,
    ) -> None:
        """Initialize the data coordinator."""
        self.base_url = base_url
        self.api_endpoint = f"{base_url}{API_ENDPOINT}"
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(self.api_endpoint)
                if response.status != 200:
                    raise UpdateFailed(
                        f"Error communicating with API: {response.status}"
                    )
                data = await response.json()
                return data

        except asyncio.TimeoutError as error:
            raise UpdateFailed(f"Timeout communicating with the API: {error}") from error

        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error communicating with API: {error}") from error

        except Exception as error:  # pylint: disable=broad-except
            raise UpdateFailed(f"Unexpected error occurred: {error}") from error 