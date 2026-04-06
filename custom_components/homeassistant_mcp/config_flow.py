"""Config flow for the Home Assistant MCP integration."""

# pyright: reportMissingImports=false, reportCallIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DEFAULT_DASHBOARD_MODE, DEFAULT_TRANSPORT, DOMAIN, TITLE


class HomeAssistantMCPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Create a single default config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title=TITLE,
            data={
                "transport": DEFAULT_TRANSPORT,
                "dashboard_mode": DEFAULT_DASHBOARD_MODE,
            },
        )
