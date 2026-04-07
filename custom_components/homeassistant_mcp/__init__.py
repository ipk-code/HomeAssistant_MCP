"""Home Assistant MCP integration."""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging
from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
except ModuleNotFoundError:  # pragma: no cover - exercised only outside HA runtime
    ConfigEntry = Any  # type: ignore[misc,assignment]
    HomeAssistant = Any  # type: ignore[misc,assignment]

from .const import DOMAIN, INTEGRATION_VERSION, STREAMABLE_HTTP_API
from .http import async_register
from .mcp.server import load_api_contract
from .runtime import create_runtime

_LOGGER = logging.getLogger(__name__)


def _runtime_root(hass: Any) -> Any:
    from pathlib import Path

    from .const import STORAGE_DIRECTORY

    if hasattr(hass, "config") and hasattr(hass.config, "path"):
        return Path(hass.config.path(STORAGE_DIRECTORY))
    return Path.cwd() / STORAGE_DIRECTORY


async def async_setup(hass: Any, config: dict) -> bool:
    """Set up the integration component."""
    async_register(hass)
    _LOGGER.info(
        "Initialized Home Assistant MCP component version %s",
        INTEGRATION_VERSION,
    )
    return True


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up the integration from a config entry."""
    async_register(hass)
    await hass.async_add_executor_job(load_api_contract)
    runtime_root = _runtime_root(hass) / entry.entry_id
    runtime = create_runtime(hass, runtime_root)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    _LOGGER.info(
        "Loaded Home Assistant MCP version %s entry %s",
        INTEGRATION_VERSION,
        entry.entry_id,
    )
    resource_payload = runtime.resources.list_payload()
    _LOGGER.info(
        "Home Assistant MCP server version %s started successfully for entry %s on %s with %s tools, %s resources, %s resource templates, %s prompts, and %s completion providers",
        INTEGRATION_VERSION,
        entry.entry_id,
        STREAMABLE_HTTP_API,
        len(runtime.registry.list_tools()),
        len(resource_payload["resources"]),
        len(resource_payload["resourceTemplates"]),
        len(runtime.prompts.list_prompts()),
        runtime.completions.provider_count(),
    )
    _LOGGER.debug("Home Assistant MCP storage path: %s", runtime_root)
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    _LOGGER.info(
        "Unloaded Home Assistant MCP version %s entry %s",
        INTEGRATION_VERSION,
        entry.entry_id,
    )
    return True
