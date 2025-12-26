"""Config flow for Azen Energy integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_SERIAL,
    DOMAIN,
    MQTT_PORT,
    MQTT_USE_TLS,
)
from .mqtt_client import AzenMQTTClient

_LOGGER = logging.getLogger(__name__)

# Schema for the configuration form
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=MQTT_PORT): int,
        vol.Required(CONF_SERIAL): str,
    }
)


class AzenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Azen Energy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Set unique ID based on serial to prevent duplicates
            serial = user_input[CONF_SERIAL]
            await self.async_set_unique_id(f"azen_{serial}")
            self._abort_if_unique_id_configured()

            # Validate MQTT connection
            try:
                client = AzenMQTTClient(
                    host=user_input[CONF_HOST],
                    port=user_input.get(CONF_PORT, MQTT_PORT),
                    serial=serial,
                    use_tls=MQTT_USE_TLS,
                )

                if not await client.connect():
                    errors["base"] = "cannot_connect"
                else:
                    await client.disconnect()
                    return self.async_create_entry(
                        title=f"Azen {serial}",
                        data=user_input,
                    )

            except Exception as err:
                _LOGGER.exception("Failed to validate MQTT connection: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
