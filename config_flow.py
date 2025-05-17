"""Config flow for Azimut Energy integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_ENDPOINT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema for the initial setup form
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=8080): int,
    }
)

# Schema for the options form
STEP_OPTIONS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_SCAN_INTERVAL, 
            default=DEFAULT_SCAN_INTERVAL
        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    port = data.get(CONF_PORT, 8080)

    api_url = f"http://{host}:{port}{API_ENDPOINT}"

    session = async_get_clientsession(hass)

    try:
        async with session.get(api_url, timeout=10) as response:
            if response.status != 200:
                raise CannotConnect(
                    f"Error connecting to API: HTTP {response.status}"
                )
            
            # Test that the response is valid JSON and contains expected data
            try:
                battery_data = await response.json()
                if (
                    "dc_voltage" not in battery_data
                    or "soc" not in battery_data
                    or "dc_current" not in battery_data
                ):
                    raise InvalidResponse(
                        "API response does not contain expected battery data"
                    )
            except ValueError:
                raise InvalidResponse("API response is not valid JSON")

    except aiohttp.ClientError as err:
        raise CannotConnect(f"Cannot connect to API: {err}") from err

    except asyncio.TimeoutError as err:
        raise CannotConnect("Timeout connecting to API") from err

    # Return info for creating entry
    return {"title": f"Victron Battery at {host}:{port}"}


class AzimutBatteryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Azimut Energy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
    
    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return AzimutBatteryOptionsFlow(config_entry)


class AzimutBatteryOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidResponse(HomeAssistantError):
    """Error to indicate the API response is invalid.""" 