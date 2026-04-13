"""Config flow for the Home Assistant MCP integration."""

# pyright: reportMissingImports=false, reportCallIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.helpers import selector

from .const import (
    CONF_ENABLE_ADMIN_FUNCTIONS,
    DEFAULT_DASHBOARD_MODE,
    DEFAULT_ENABLE_ADMIN_FUNCTIONS,
    DEFAULT_TRANSPORT,
    DOMAIN,
    TITLE,
)


def _settings_schema(default: bool) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_ENABLE_ADMIN_FUNCTIONS,
                default=default,
            ): selector.BooleanSelector(),
        }
    )


class HomeAssistantMCPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Create a single default config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_settings_schema(DEFAULT_ENABLE_ADMIN_FUNCTIONS),
            )

        return self.async_create_entry(
            title=TITLE,
            data={
                "transport": DEFAULT_TRANSPORT,
                "dashboard_mode": DEFAULT_DASHBOARD_MODE,
                CONF_ENABLE_ADMIN_FUNCTIONS: bool(
                    user_input[CONF_ENABLE_ADMIN_FUNCTIONS]
                ),
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return HomeAssistantMCPOptionsFlow(config_entry)


class HomeAssistantMCPOptionsFlow(OptionsFlowWithReload):
    """Handle options for Home Assistant MCP."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_ENABLE_ADMIN_FUNCTIONS: bool(
                        user_input[CONF_ENABLE_ADMIN_FUNCTIONS]
                    )
                },
            )

        default = self._config_entry.options.get(
            CONF_ENABLE_ADMIN_FUNCTIONS,
            self._config_entry.data.get(
                CONF_ENABLE_ADMIN_FUNCTIONS, DEFAULT_ENABLE_ADMIN_FUNCTIONS
            ),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(bool(default)),
        )
