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


class _FakeNativeLovelaceProvider:
    async def list_dashboards(self, *, limit: int = 200) -> dict:
        return {
            "dashboards": [
                {
                    "id": "pv_energy",
                    "title": "Photovoltaik",
                    "url_path": "pv-energy",
                    "mode": "storage",
                    "source": "home_assistant_lovelace",
                    "view_count": 2,
                }
            ],
            "truncated": False,
        }

    async def get_dashboard(self, url_path: str) -> dict:
        if url_path != "pv-energy":
            raise KeyError(f"unknown lovelace dashboard: {url_path}")
        return {
            "metadata": {
                "id": "pv_energy",
                "title": "Photovoltaik",
                "url_path": "pv-energy",
                "mode": "storage",
                "source": "home_assistant_lovelace",
                "view_count": 2,
            },
            "config": {"views": []},
        }


class _FakeFrontendPanelsProvider:
    def list_panels(self, *, user=None, limit: int = 200) -> dict:
        return {
            "panels": [
                {
                    "component_name": "energy",
                    "default_visible": True,
                    "url_path": "energy",
                    "require_admin": False,
                    "source": "home_assistant_frontend",
                    "panel_kind": "built_in",
                }
            ],
            "truncated": False,
        }

    def get_panel(self, url_path: str, *, user=None) -> dict:
        if url_path != "energy":
            raise KeyError(f"unknown frontend panel: {url_path}")
        return {
            "component_name": "energy",
            "default_visible": True,
            "url_path": "energy",
            "require_admin": False,
            "source": "home_assistant_frontend",
            "panel_kind": "built_in",
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


class BuiltinAsyncResourceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addAsyncCleanup(self._cleanup_tempdir)
        self.repository = YamlDashboardRepository(self.tempdir.name)
        self.repository.create_dashboard(
            {
                "dashboard_id": "main",
                "title": "Main",
                "url_path": "main",
                "views": [],
            }
        )

    async def _cleanup_tempdir(self) -> None:
        self.tempdir.cleanup()

    async def test_builtin_native_resources_return_async_payloads(self) -> None:
        registry = ResourceRegistry()
        register_builtin_resources(
            registry,
            repository=self.repository,
            discovery=_FakeDiscoveryProvider(),
            native=_FakeNativeLovelaceProvider(),
            frontend=_FakeFrontendPanelsProvider(),
        )

        payload = registry.list_payload()
        self.assertIn(
            "hass://lovelace/dashboards", [item["uri"] for item in payload["resources"]]
        )
        self.assertIn(
            "hass://frontend/panels", [item["uri"] for item in payload["resources"]]
        )
        self.assertEqual(
            payload["resourceTemplates"][1]["uriTemplate"],
            "hass://lovelace/dashboard/{url_path}",
        )
        self.assertEqual(
            payload["resourceTemplates"][2]["uriTemplate"],
            "hass://frontend/panel/{url_path}",
        )

        native_dashboards = json.loads(
            (await registry.async_read("hass://lovelace/dashboards"))[0]["text"]
        )
        self.assertEqual(native_dashboards["dashboards"][0]["id"], "pv_energy")

        native_dashboard = json.loads(
            (await registry.async_read("hass://lovelace/dashboard/pv-energy"))[0][
                "text"
            ]
        )
        self.assertEqual(native_dashboard["metadata"]["url_path"], "pv-energy")

        frontend_panels = json.loads(
            (await registry.async_read("hass://frontend/panels"))[0]["text"]
        )
        self.assertEqual(frontend_panels["panels"][0]["url_path"], "energy")

        frontend_panel = json.loads(
            (await registry.async_read("hass://frontend/panel/energy"))[0]["text"]
        )
        self.assertEqual(frontend_panel["url_path"], "energy")
