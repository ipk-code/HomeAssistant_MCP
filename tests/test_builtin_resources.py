"""Tests for built-in MCP resources."""

from __future__ import annotations

import json
from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp.lovelace.repository import (
    YamlDashboardRepository,
)
from custom_components.homeassistant_mcp.mcp.resources import (
    ResourceRegistry,
    register_builtin_resources,
)


class _FakeDiscoveryProvider:
    def list_entities(self, arguments: dict) -> dict:
        return {
            "entities": [{"entity_id": "sensor.kitchen_temperature"}],
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

    def list_services(self, arguments: dict) -> dict:
        return {
            "services": [{"domain": "light", "services": ["turn_on"]}],
            "truncated": False,
        }


class BuiltinResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.repository = YamlDashboardRepository(self.tempdir.name)
        self.repository.create_dashboard(
            {
                "dashboard_id": "main",
                "title": "Main",
                "url_path": "main",
                "views": [],
            }
        )
        self.registry = ResourceRegistry()
        register_builtin_resources(
            self.registry,
            repository=self.repository,
            discovery=_FakeDiscoveryProvider(),
        )

    def test_builtin_resource_listing_includes_static_and_template_resources(
        self,
    ) -> None:
        payload = self.registry.list_payload()
        self.assertEqual(
            [item["uri"] for item in payload["resources"]],
            [
                "hass://config",
                "hass://entities",
                "hass://areas",
                "hass://devices",
                "hass://services",
            ],
        )
        self.assertEqual(
            payload["resourceTemplates"][0]["uriTemplate"],
            "hass://dashboard/{dashboard_id}",
        )

    def test_builtin_resource_reads_return_json_payloads(self) -> None:
        config_payload = json.loads(self.registry.read("hass://config")[0]["text"])
        self.assertEqual(config_payload["integration"]["domain"], "homeassistant_mcp")
        self.assertEqual(config_payload["defaults"]["completion_max_values"], 25)

        entities_payload = json.loads(self.registry.read("hass://entities")[0]["text"])
        self.assertEqual(
            entities_payload["entities"][0]["entity_id"],
            "sensor.kitchen_temperature",
        )

        dashboard_payload = json.loads(
            self.registry.read("hass://dashboard/main")[0]["text"]
        )
        self.assertEqual(dashboard_payload["metadata"]["dashboard_id"], "main")

    def test_unknown_template_resource_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown resource"):
            self.registry.read("hass://dashboard/missing")
