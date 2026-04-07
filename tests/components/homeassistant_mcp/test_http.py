"""Real Home Assistant HTTP endpoint tests."""

# pyright: reportMissingImports=false

from __future__ import annotations

import json

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
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
    assert [item["uri"] for item in resources_payload["result"]["resources"]] == [
        "hass://config",
        "hass://entities",
        "hass://areas",
        "hass://devices",
        "hass://services",
        "hass://lovelace/dashboards",
    ]
    assert resources_payload["result"]["resourceTemplates"] == [
        {
            "uriTemplate": "hass://dashboard/{dashboard_id}",
            "name": "Managed Dashboard",
            "description": "A managed Lovelace dashboard document by dashboard identifier.",
            "mimeType": "application/json",
        },
        {
            "uriTemplate": "hass://lovelace/dashboard/{url_path}",
            "name": "Native Lovelace Dashboard",
            "description": "A native Home Assistant Lovelace dashboard document by url_path.",
            "mimeType": "application/json",
        },
    ]

    prompts_response = await client.post(
        STREAMABLE_HTTP_API,
        json={"jsonrpc": "2.0", "id": "2", "method": "prompts/list", "params": {}},
        headers={"Accept": "application/json"},
    )
    assert prompts_response.status == 200
    prompts_payload = await prompts_response.json()
    assert [item["name"] for item in prompts_payload["result"]["prompts"]] == [
        "dashboard.builder",
        "dashboard.review",
        "dashboard.layout_consistency_review",
        "dashboard.entity_card_mapping",
        "dashboard.cleanup_audit",
    ]

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


async def test_streamable_http_builtin_prompts_return_contextual_results(
    hass, hass_client
) -> None:
    """Test built-in prompts over the real HA HTTP stack."""
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

    hass.states.async_set(
        "sensor.kitchen_temperature",
        "21",
        {
            "friendly_name": "Kitchen Temperature",
            "device_class": "temperature",
        },
    )

    client = await hass_client()
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
    assert create_response.status == 200

    review_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "prompts/get",
            "params": {
                "name": "dashboard.review",
                "arguments": {"dashboard_id": "main"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert review_response.status == 200
    review_payload = await review_response.json()
    review_text = review_payload["result"]["messages"][0]["content"]["text"]
    assert "hass://dashboard/main" in review_text
    assert '"view_id": "overview"' in review_text

    mapping_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "prompts/get",
            "params": {
                "name": "dashboard.entity_card_mapping",
                "arguments": {"entity_id": "sensor.kitchen_temperature"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert mapping_response.status == 200
    mapping_payload = await mapping_response.json()
    mapping_text = mapping_payload["result"]["messages"][0]["content"]["text"]
    assert "gauge" in mapping_text
    assert "tile" in mapping_text

    missing_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "prompts/get",
            "params": {
                "name": "dashboard.review",
                "arguments": {"dashboard_id": "missing"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert missing_response.status == 400
    missing_payload = await missing_response.json()
    assert missing_payload["error"]["code"] == -32602


async def test_streamable_http_builtin_resources_return_json_payloads(
    hass, hass_client
) -> None:
    """Test built-in MCP resources over the real HA stack."""
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

    hass.states.async_set(
        "sensor.kitchen_temperature",
        "21",
        {"friendly_name": "Kitchen Temperature"},
    )

    client = await hass_client()
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

    config_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "resources/read",
            "params": {"uri": "hass://config"},
        },
        headers={"Accept": "application/json"},
    )
    assert config_response.status == 200
    config_payload = await config_response.json()
    config_result = json.loads(config_payload["result"]["contents"][0]["text"])
    assert config_result["integration"]["domain"] == DOMAIN

    entities_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "resources/read",
            "params": {"uri": "hass://entities"},
        },
        headers={"Accept": "application/json"},
    )
    assert entities_response.status == 200
    entities_payload = await entities_response.json()
    entities_result = json.loads(entities_payload["result"]["contents"][0]["text"])
    assert entities_result["entities"][0]["entity_id"] == "sensor.kitchen_temperature"

    dashboard_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "resources/read",
            "params": {"uri": "hass://dashboard/main"},
        },
        headers={"Accept": "application/json"},
    )
    assert dashboard_response.status == 200
    dashboard_payload = await dashboard_response.json()
    dashboard_result = json.loads(dashboard_payload["result"]["contents"][0]["text"])
    assert dashboard_result["metadata"]["dashboard_id"] == "main"

    missing_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "5",
            "method": "resources/read",
            "params": {"uri": "hass://dashboard/missing"},
        },
        headers={"Accept": "application/json"},
    )
    assert missing_response.status == 400
    missing_payload = await missing_response.json()
    assert missing_payload["error"]["code"] == -32602

    invalid_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "6",
            "method": "resources/read",
            "params": {"uri": "hass://dashboard/Energie"},
        },
        headers={"Accept": "application/json"},
    )
    assert invalid_response.status == 400
    invalid_payload = await invalid_response.json()
    assert invalid_payload["error"]["code"] == -32602


async def test_streamable_http_native_lovelace_dashboards_are_available_read_only(
    hass, hass_client
) -> None:
    """Test read-only access to native Home Assistant Lovelace dashboards."""
    assert await async_setup_component(
        hass, "lovelace", {"lovelace": {"mode": "storage"}}
    )
    await hass.async_block_till_done()

    from homeassistant.components.lovelace.const import LOVELACE_DATA

    class _NativeDashboardFixture:
        url_path = "pv-energy"
        config = {
            "id": "pv_energy",
            "title": "Photovoltaik",
            "show_in_sidebar": True,
            "icon": "mdi:solar-power",
        }

        async def async_get_info(self):
            return {"mode": "storage", "views": 1}

        async def async_load(self, force):
            return {"views": [{"title": "Solar Dashboard"}]}

    hass.data[LOVELACE_DATA].dashboards["pv-energy"] = _NativeDashboardFixture()

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

    list_tool_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "hass.list_lovelace_dashboards",
                "arguments": {},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert list_tool_response.status == 200
    list_tool_payload = await list_tool_response.json()
    list_tool_result = _decode_tool_result(list_tool_payload)
    _VALIDATOR.validate_tool_result("hass.list_lovelace_dashboards", list_tool_result)
    assert any(
        item["url_path"] == "pv-energy" for item in list_tool_result["dashboards"]
    )

    get_tool_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "hass.get_lovelace_dashboard",
                "arguments": {"url_path": "pv-energy"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert get_tool_response.status == 200
    get_tool_payload = await get_tool_response.json()
    get_tool_result = _decode_tool_result(get_tool_payload)
    _VALIDATOR.validate_tool_result("hass.get_lovelace_dashboard", get_tool_result)
    assert get_tool_result["dashboard"]["metadata"]["url_path"] == "pv-energy"

    resource_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "resources/read",
            "params": {"uri": "hass://lovelace/dashboards"},
        },
        headers={"Accept": "application/json"},
    )
    assert resource_response.status == 200
    resource_payload = await resource_response.json()
    resource_result = json.loads(resource_payload["result"]["contents"][0]["text"])
    assert any(
        item["url_path"] == "pv-energy" for item in resource_result["dashboards"]
    )

    dashboard_resource_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "resources/read",
            "params": {"uri": "hass://lovelace/dashboard/pv-energy"},
        },
        headers={"Accept": "application/json"},
    )
    assert dashboard_resource_response.status == 200
    dashboard_resource_payload = await dashboard_resource_response.json()
    dashboard_resource_result = json.loads(
        dashboard_resource_payload["result"]["contents"][0]["text"]
    )
    assert dashboard_resource_result["metadata"]["url_path"] == "pv-energy"


async def test_streamable_http_builtin_completions_return_contextual_results(
    hass, hass_client
) -> None:
    """Test authenticated built-in completion providers over the real HA stack."""
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

    hass.states.async_set(
        "sensor.kitchen_temperature",
        "21",
        {"friendly_name": "Kitchen Temperature"},
    )

    client = await hass_client()
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
    assert create_response.status == 200
    create_payload = await create_response.json()
    card_id = _decode_tool_result(create_payload)["views"][0]["cards"][0]["card_id"]

    entity_completion = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "completion/complete",
            "params": {
                "ref": {"name": "lovelace.create_card"},
                "argument": {"name": "entity_id", "value": "sensor.k"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert entity_completion.status == 200
    entity_payload = await entity_completion.json()
    assert entity_payload["result"]["completion"]["values"] == [
        "sensor.kitchen_temperature"
    ]

    dashboard_completion = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "completion/complete",
            "params": {
                "ref": {"name": "lovelace.get_dashboard"},
                "argument": {"name": "dashboard_id", "value": "ma"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert dashboard_completion.status == 200
    dashboard_payload = await dashboard_completion.json()
    assert dashboard_payload["result"]["completion"]["values"] == ["main"]

    view_completion = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "completion/complete",
            "params": {
                "ref": {
                    "name": "lovelace.get_view",
                    "arguments": {"dashboard_id": "main"},
                },
                "argument": {"name": "view_id", "value": "ov"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert view_completion.status == 200
    view_payload = await view_completion.json()
    assert view_payload["result"]["completion"]["values"] == ["overview"]

    card_completion = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "5",
            "method": "completion/complete",
            "params": {
                "ref": {
                    "name": "lovelace.get_card",
                    "arguments": {"dashboard_id": "main", "view_id": "overview"},
                },
                "argument": {"name": "card_id", "value": card_id[:8]},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert card_completion.status == 200
    card_payload = await card_completion.json()
    assert card_payload["result"]["completion"]["values"] == [card_id]

    icon_completion = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "6",
            "method": "completion/complete",
            "params": {
                "ref": {"name": "lovelace.create_dashboard"},
                "argument": {"name": "icon", "value": "mdi:th"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert icon_completion.status == 200
    icon_payload = await icon_completion.json()
    assert icon_payload["result"]["completion"]["values"] == ["mdi:thermometer"]


async def test_streamable_http_hass_discovery_tools_return_valid_results(
    hass, hass_client
) -> None:
    """Test authenticated read-only Home Assistant discovery tools."""
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

    area_registry = ar.async_get(hass)
    area = area_registry.async_create("Kitchen")

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "kitchen-hub")},
        manufacturer="Acme",
        model="Hub",
        name="Kitchen Hub",
    )
    device = device_registry.async_update_device(device.id, area_id=area.id)

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "kitchen-temperature",
        suggested_object_id="kitchen_temperature",
        config_entry=entry,
        device_id=device.id,
        original_name="Kitchen Temperature",
        original_device_class="temperature",
        unit_of_measurement="C",
    )

    hass.states.async_set(
        "sensor.kitchen_temperature",
        "21",
        {
            "friendly_name": "Kitchen Temperature",
            "device_class": "temperature",
            "unit_of_measurement": "C",
        },
    )
    hass.states.async_set(
        "light.porch",
        "off",
        {"friendly_name": "Porch Light"},
    )

    async def _handle_light_turn_on(call):
        return None

    hass.services.async_register("light", "turn_on", _handle_light_turn_on)
    await hass.async_block_till_done()

    client = await hass_client()

    entities_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "hass.list_entities",
                "arguments": {"area_id": area.id},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert entities_response.status == 200
    entities_payload = await entities_response.json()
    entities_result = _decode_tool_result(entities_payload)
    _VALIDATOR.validate_tool_result("hass.list_entities", entities_result)
    assert entities_result["entities"][0]["entity_id"] == "sensor.kitchen_temperature"

    search_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "hass.search_entities",
                "arguments": {"query": "kitchen"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert search_response.status == 200
    search_payload = await search_response.json()
    search_result = _decode_tool_result(search_payload)
    _VALIDATOR.validate_tool_result("hass.search_entities", search_result)
    assert search_result["entities"][0]["entity_id"] == "sensor.kitchen_temperature"

    services_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "hass.list_services",
                "arguments": {"domain": "light"},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert services_response.status == 200
    services_payload = await services_response.json()
    services_result = _decode_tool_result(services_payload)
    _VALIDATOR.validate_tool_result("hass.list_services", services_result)
    assert "turn_on" in services_result["services"][0]["services"]

    areas_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "tools/call",
            "params": {"name": "hass.list_areas", "arguments": {}},
        },
        headers={"Accept": "application/json"},
    )
    assert areas_response.status == 200
    areas_payload = await areas_response.json()
    areas_result = _decode_tool_result(areas_payload)
    _VALIDATOR.validate_tool_result("hass.list_areas", areas_result)
    assert any(item["name"] == "Kitchen" for item in areas_result["areas"])

    devices_response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "5",
            "method": "tools/call",
            "params": {
                "name": "hass.list_devices",
                "arguments": {"area_id": area.id},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert devices_response.status == 200
    devices_payload = await devices_response.json()
    devices_result = _decode_tool_result(devices_payload)
    _VALIDATOR.validate_tool_result("hass.list_devices", devices_result)
    assert devices_result["devices"][0]["device_id"] == device.id


async def test_streamable_http_hass_discovery_tools_respect_limit(
    hass, hass_client
) -> None:
    """Test bounded list responses from the discovery tool surface."""
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

    hass.states.async_set("sensor.one", "1", {"friendly_name": "One"})
    hass.states.async_set("sensor.two", "2", {"friendly_name": "Two"})
    await hass.async_block_till_done()

    client = await hass_client()
    response = await client.post(
        STREAMABLE_HTTP_API,
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "hass.list_entities",
                "arguments": {"domain": "sensor", "limit": 1},
            },
        },
        headers={"Accept": "application/json"},
    )
    assert response.status == 200
    payload = await response.json()
    result = _decode_tool_result(payload)
    _VALIDATOR.validate_tool_result("hass.list_entities", result)
    assert len(result["entities"]) == 1
    assert result["truncated"] is True


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
