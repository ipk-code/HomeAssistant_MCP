"""Tests for tool contract loading and registry dispatch."""

from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp.lovelace.repository import (
    YamlDashboardRepository,
)
from custom_components.homeassistant_mcp.mcp.server import (
    ToolRegistry,
    load_api_contract,
)


class _FakeDiscoveryProvider:
    def list_entities(self, arguments: dict) -> dict:
        return {"entities": [{"entity_id": "light.kitchen"}], "truncated": False}

    def search_entities(self, arguments: dict) -> dict:
        return {
            "entities": [{"entity_id": "sensor.kitchen_temperature"}],
            "truncated": False,
        }

    def list_services(self, arguments: dict) -> dict:
        return {
            "services": [{"domain": "light", "services": ["turn_on"]}],
            "truncated": False,
        }

    def list_areas(self, arguments: dict) -> dict:
        return {
            "areas": [{"area_id": "kitchen", "name": "Kitchen"}],
            "truncated": False,
        }

    def list_devices(self, arguments: dict) -> dict:
        return {
            "devices": [{"device_id": "device-1", "name": "Kitchen Hub"}],
            "truncated": False,
        }


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        repository = YamlDashboardRepository(self.tempdir.name)
        self.registry = ToolRegistry(repository, discovery=_FakeDiscoveryProvider())

    def test_contract_loader_exposes_all_tools(self) -> None:
        payload, tools = load_api_contract()
        self.assertEqual(payload["api_version"], "1.0.0")
        self.assertEqual(len(tools), 32)
        self.assertEqual(tools[0].name, "lovelace.list_dashboards")

    def test_registry_lists_serialized_tools(self) -> None:
        tools = self.registry.list_tools()
        self.assertEqual(len(tools), 32)
        self.assertEqual(tools[0]["name"], "lovelace.list_dashboards")
        self.assertIn("inputSchema", tools[0])
        validate_tool = next(
            tool for tool in tools if tool["name"] == "lovelace.validate_dashboard"
        )
        self.assertEqual(validate_tool["inputSchema"]["type"], "object")
        frontend_tool = next(
            tool for tool in tools if tool["name"] == "hass.list_frontend_panels"
        )
        self.assertEqual(
            frontend_tool["inputSchema"]["properties"]["limit"]["$ref"],
            "#/$defs/result_limit",
        )
        native_create_tool = next(
            tool for tool in tools if tool["name"] == "hass.create_lovelace_dashboard"
        )
        self.assertEqual(
            native_create_tool["inputSchema"]["properties"]["url_path"]["$ref"],
            "#/$defs/native_lovelace_storage_url_path",
        )

    def test_registry_dispatches_hass_discovery_calls(self) -> None:
        entities = self.registry.call("hass.list_entities", {})
        self.assertEqual(entities["entities"][0]["entity_id"], "light.kitchen")

        devices = self.registry.call("hass.list_devices", {})
        self.assertEqual(devices["devices"][0]["device_id"], "device-1")

    def test_registry_without_discovery_rejects_hass_calls(self) -> None:
        repository = YamlDashboardRepository(self.tempdir.name)
        registry = ToolRegistry(repository)
        with self.assertRaisesRegex(KeyError, "discovery provider is unavailable"):
            registry.call("hass.list_entities", {})

    def test_registry_dispatches_dashboard_and_card_calls(self) -> None:
        dashboard = self.registry.call(
            "lovelace.create_dashboard",
            {
                "dashboard_id": "main",
                "title": "Main",
                "url_path": "main",
                "views": [
                    {
                        "view_id": "overview",
                        "title": "Overview",
                        "path": "overview",
                        "cards": [],
                    }
                ],
            },
        )
        self.assertEqual(dashboard["metadata"]["dashboard_id"], "main")

        result = self.registry.call(
            "lovelace.create_card",
            {
                "dashboard_id": "main",
                "view_id": "overview",
                "expected_version": 0,
                "card": {"kind": "tile", "entity_id": "light.kitchen"},
            },
        )
        self.assertEqual(result["dashboard_id"], "main")
        self.assertEqual(result["view_id"], "overview")
        self.assertEqual(result["card"]["kind"], "tile")

    def test_validate_dashboard_tool_returns_normalized_document(self) -> None:
        normalized = self.registry.call(
            "lovelace.validate_dashboard",
            {
                "dashboard": {
                    "metadata": {
                        "dashboard_id": "main",
                        "title": "Main",
                        "url_path": "main",
                        "mode": "yaml",
                        "show_in_sidebar": True,
                        "require_admin": False,
                    },
                    "views": [],
                    "dashboard_version": 0,
                }
            },
        )
        self.assertTrue(normalized["valid"])
        self.assertEqual(
            normalized["normalized_dashboard"]["metadata"]["dashboard_id"], "main"
        )
