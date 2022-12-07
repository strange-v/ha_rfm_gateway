"""Config flow for RFM Gateway."""
from __future__ import annotations

import logging
import re
from re import Match
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_GATEWAYS, DOMAIN, GW_NAME, STORE

_LOGGER = logging.getLogger(__name__)

GATEWAY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional("add_another"): cv.boolean,
    }
)


class GatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """RFM Gateway config flow."""

    def __init__(self) -> None:
        """Ititialization of GatewayConfigFlow."""
        super().__init__()
        self.data: dict[str, Any] = {CONF_GATEWAYS: [], STORE: {}}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a gateway."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not check_is_mac_valid(user_input[CONF_MAC]):
                errors["base"] = "invalid_mac"
            elif not check_is_mac_unique(
                user_input[CONF_MAC], self.data[CONF_GATEWAYS]
            ):
                errors["base"] = "mac_not_unique"

            if not errors:
                self.data[CONF_GATEWAYS].append(
                    {
                        "mac": user_input[CONF_MAC],
                        "name": user_input.get(CONF_NAME, GW_NAME),
                    }
                )

                if user_input.get("add_another", False):
                    return await self.async_step_user()

                return self.async_create_entry(title=GW_NAME, data=self.data)

        return self.async_show_form(
            step_id="user", data_schema=GATEWAY_SCHEMA, errors=errors
        )


def check_is_mac_valid(mac: str) -> Match[str] | None:
    """Check MAC address for validity."""
    return re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower())


def check_is_mac_unique(mac: str, data: list[str]) -> bool:
    """Check MAC address for uniqueness."""
    for current_mac in data:
        if current_mac == mac:
            return False
    return True
