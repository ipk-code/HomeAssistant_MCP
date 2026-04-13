"""Real Home Assistant config-entry lifecycle tests."""

from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homeassistant_mcp.const import (
    CONF_ENABLE_ADMIN_FUNCTIONS,
    DEFAULT_DASHBOARD_MODE,
    DEFAULT_ENABLE_ADMIN_FUNCTIONS,
    DEFAULT_TRANSPORT,
    DOMAIN,
    STORAGE_DIRECTORY,
)


async def test_setup_and_unload_entry(hass) -> None:
    """Test setting up and unloading a real config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "transport": DEFAULT_TRANSPORT,
            "dashboard_mode": DEFAULT_DASHBOARD_MODE,
            CONF_ENABLE_ADMIN_FUNCTIONS: DEFAULT_ENABLE_ADMIN_FUNCTIONS,
        },
        title="Home Assistant MCP",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert (
        runtime.root_path == Path(hass.config.path(STORAGE_DIRECTORY)) / entry.entry_id
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert hass.data[DOMAIN] == {}
