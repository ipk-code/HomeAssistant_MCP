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
from custom_components.homeassistant_mcp.mcp.schema import ToolSchemaValidator
from custom_components.homeassistant_mcp.mcp.server import load_api_contract

_SPEC, _ = load_api_contract()
_VALIDATOR = ToolSchemaValidator(_SPEC)


def _decode_tool_result(payload: dict) -> dict:
    return json.loads(payload["result"]["content"][0]["text"])


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
    create_result = _decode_tool_result(create_payload)
    _VALIDATOR.validate_tool_result("lovelace.create_dashboard", create_result)

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
    dashboards = _decode_tool_result(list_payload)
    _VALIDATOR.validate_tool_result("lovelace.list_dashboards", dashboards)
    assert dashboards["dashboards"][0]["dashboard_id"] == "main"


async def test_streamable_http_validates_view_response_shape(hass, hass_client) -> None:
    """Test real HTTP tool results match the published output schema."""
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

    create_view_response = await client.post(
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
                    "views": [
                        {
                            "view_id": "overview",
                            "title": "Overview",
                            "path": "overview",
                            "cards": [{"kind": "heading", "title": "Welcome"}],
                        }
                    ],
                },
            },
        },
        headers={"Accept": "application/json"},
    )
    assert create_view_response.status == 200

    get_view_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "lovelace.get_view",
                "arguments": {"dashboard_id": "main", "view_id": "overview"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert get_view_response.status == 200
    get_view_payload = await get_view_response.json()
    view_result = _decode_tool_result(get_view_payload)
    _VALIDATOR.validate_tool_result("lovelace.get_view", view_result)
    assert view_result["view"]["view_id"] == "overview"


async def test_streamable_http_supports_phase2_capability_methods(
    hass, hass_client
) -> None:
    """Test authenticated resources, prompts, and completions dispatch over HA HTTP."""
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

    resources_response = await client.post(
        STREAMABLE_HTTP_API,
        json={"jsonrpc": "2.0", "id": "1", "method": "resources/list", "params": {}},
        headers={"Accept": "application/json"},
    )
    assert resources_response.status == 200
    resources_payload = await resources_response.json()
    assert resources_payload["result"] == {"resources": [], "resourceTemplates": []}

    prompts_response = await client.post(
        STREAMABLE_HTTP_API,
        json={"jsonrpc": "2.0", "id": "2", "method": "prompts/list", "params": {}},
        headers={"Accept": "application/json"},
    )
    assert prompts_response.status == 200
    prompts_payload = await prompts_response.json()
    assert prompts_payload["result"] == {"prompts": []}

    completion_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "completion/complete",
            "params": {
                "ref": {"name": "dashboard.review"},
                "argument": {"name": "dashboard_id"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert completion_response.status == 200
    completion_payload = await completion_response.json()
    assert completion_payload["result"] == {
        "completion": {"values": [], "hasMore": False}
    }


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
