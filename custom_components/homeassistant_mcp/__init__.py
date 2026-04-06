"""Home Assistant MCP integration."""

# pyright: reportMissingImports=false

from __future__ import annotations

from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
except ModuleNotFoundError:  # pragma: no cover - exercised only outside HA runtime
    ConfigEntry = Any  # type: ignore[misc,assignment]
    HomeAssistant = Any  # type: ignore[misc,assignment]

from .const import DOMAIN

async def async_setup(hass: Any, config: dict) -> bool:
    """Set up the integration component."""
    return True


async def async_setup_entry(
    hass: Any, entry: Any
) -> bool:
    """Set up the integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = None
    return True


async def async_unload_entry(
    hass: Any, entry: Any
) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
