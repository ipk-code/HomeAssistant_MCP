"""Home Assistant MCP integration."""

# pyright: reportMissingImports=false

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

type HomeAssistantMCPConfigEntry = ConfigEntry[None]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration component."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: HomeAssistantMCPConfigEntry
) -> bool:
    """Set up the integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = None
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HomeAssistantMCPConfigEntry
) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
