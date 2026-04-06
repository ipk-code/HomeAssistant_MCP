"""Real Home Assistant HTTP endpoint tests."""

# pyright: reportMissingImports=false

from __future__ import annotations

import json

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homeassistant_mcp.const import (
    DEFAULT_DASHBOARD_MODE,
    DEFAULT_TRANSPORT,
    DOMAIN,
    STREAMABLE_HTTP_API,
)


async def test_streamable_http_requires_auth(hass, hass_client_no_auth) -> None:
    """Test the MCP endpoint rejects unauthenticated requests."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    client = await hass_client_no_auth()
    response = await client.post(
        STREAMABLE_HTTP_API,
        json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}},
        headers={"Accept": "application/json"},
    )

    assert response.status == 401


async def test_streamable_http_tool_round_trip(hass, hass_client) -> None:
    """Test the authenticated MCP endpoint against the real HA HTTP stack."""
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

    response = await client.get(STREAMABLE_HTTP_API)
    assert response.status == 405

    create_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "lovelace.create_dashboard",
                "arguments": {
                    "dashboard_id": "main",
                    "title": "Main",
                    "url_path": "main",
                    "views": [],
                },
            },
        },
        headers={"Accept": "application/json"},
    )
    assert create_response.status == 200
    create_payload = await create_response.json()
    assert create_payload["result"]["isError"] is False

    list_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {"name": "lovelace.list_dashboards", "arguments": {}},
        },
        headers={"Accept": "application/json"},
    )
    assert list_response.status == 200
    list_payload = await list_response.json()
    dashboards = json.loads(list_payload["result"]["content"][0]["text"])
    assert dashboards["dashboards"][0]["dashboard_id"] == "main"


async def test_streamable_http_returns_jsonrpc_error_for_invalid_payload(
    hass, hass_client
) -> None:
    """Test malformed JSON-RPC requests against the real HA HTTP stack."""
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
    response = await client.post(
        STREAMABLE_HTTP_API,
        data="{",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert response.status == 400
    payload = await response.json()
    assert payload["error"]["code"] == -32700
