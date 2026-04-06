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
from .http import async_register
from .runtime import create_runtime


def _runtime_root(hass: Any) -> Any:
    from pathlib import Path

    from .const import STORAGE_DIRECTORY

    if hasattr(hass, "config") and hasattr(hass.config, "path"):
        return Path(hass.config.path(STORAGE_DIRECTORY))
    return Path.cwd() / STORAGE_DIRECTORY

async def async_setup(hass: Any, config: dict) -> bool:
    """Set up the integration component."""
    async_register(hass)
    return True


async def async_setup_entry(
    hass: Any, entry: Any
) -> bool:
    """Set up the integration from a config entry."""
    async_register(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = create_runtime(
        _runtime_root(hass) / entry.entry_id
    )
    return True


async def async_unload_entry(
    hass: Any, entry: Any
) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
