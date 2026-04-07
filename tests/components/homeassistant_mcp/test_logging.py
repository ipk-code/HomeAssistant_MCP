"""Real Home Assistant logging tests."""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homeassistant_mcp.const import (
    DEFAULT_DASHBOARD_MODE,
    DEFAULT_TRANSPORT,
    DOMAIN,
    INTEGRATION_VERSION,
)


async def test_entry_setup_and_unload_emit_lifecycle_logs(hass, caplog) -> None:
    """Test lifecycle logs are emitted through Home Assistant runtime setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "transport": DEFAULT_TRANSPORT,
            "dashboard_mode": DEFAULT_DASHBOARD_MODE,
        },
        title="Home Assistant MCP",
    )
    entry.add_to_hass(hass)

    caplog.set_level(logging.INFO, logger="custom_components.homeassistant_mcp")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert (
        f"Registered Home Assistant MCP HTTP view version {INTEGRATION_VERSION} at /api/homeassistant_mcp"
        in caplog.text
    )
    assert (
        f"Loaded Home Assistant MCP version {INTEGRATION_VERSION} entry {entry.entry_id}"
        in caplog.text
    )
    assert (
        f"Home Assistant MCP server version {INTEGRATION_VERSION} started successfully for entry {entry.entry_id} on /api/homeassistant_mcp"
        in caplog.text
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert (
        f"Unloaded Home Assistant MCP version {INTEGRATION_VERSION} entry {entry.entry_id}"
        in caplog.text
    )


async def test_invalid_http_payload_emits_warning_log(
    hass, hass_client, caplog
) -> None:
    """Test malformed MCP requests are logged at warning level."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "transport": DEFAULT_TRANSPORT,
            "dashboard_mode": DEFAULT_DASHBOARD_MODE,
        },
        title="Home Assistant MCP",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_client()
    caplog.set_level(logging.WARNING, logger="custom_components.homeassistant_mcp")

    response = await client.post(
        "/api/homeassistant_mcp",
        data="{",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert response.status == 400
    assert "Rejected MCP request because body was not valid JSON" in caplog.text
