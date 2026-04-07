"""Tests for built-in MCP prompts."""

from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp.mcp.prompts import (
    PromptRegistry,
    register_builtin_prompts,
)
from custom_components.homeassistant_mcp.lovelace.repository import (
    YamlDashboardRepository,
)


class _FakeDiscoveryProvider:
    def list_areas(self, arguments: dict) -> dict:
        return {
            "areas": [{"area_id": "kitchen", "name": "Kitchen"}],
            "truncated": False,
        }

    def get_entity_summary(self, entity_id: str) -> dict:
        if entity_id != "sensor.kitchen_temperature":
            raise KeyError(f"unknown entity: {entity_id}")
        return {
            "entity_id": entity_id,
            "domain": "sensor",
            "state": "21",
            "friendly_name": "Kitchen Temperature",
            "device_class": "temperature",
        }


class BuiltinPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.repository = YamlDashboardRepository(self.tempdir.name)
        self.repository.create_dashboard(
            {
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
            }
        )
        self.registry = PromptRegistry()
        register_builtin_prompts(
            self.registry,
            repository=self.repository,
            discovery=_FakeDiscoveryProvider(),
        )

    def test_builtin_prompt_listing_exposes_catalog(self) -> None:
        prompts = self.registry.list_prompts()
        self.assertEqual(
            [prompt["name"] for prompt in prompts],
            [
                "dashboard.builder",
                "dashboard.review",
                "dashboard.layout_consistency_review",
                "dashboard.entity_card_mapping",
                "dashboard.cleanup_audit",
            ],
        )

    def test_dashboard_review_prompt_contains_dashboard_context(self) -> None:
        payload = self.registry.get("dashboard.review", {"dashboard_id": "main"})
        text = payload["messages"][0]["content"]["text"]
        self.assertIn("hass://dashboard/main", text)
        self.assertIn('"view_id": "overview"', text)

    def test_entity_card_mapping_prompt_contains_supported_card_suggestions(
        self,
    ) -> None:
        payload = self.registry.get(
            "dashboard.entity_card_mapping",
            {"entity_id": "sensor.kitchen_temperature"},
        )
        text = payload["messages"][0]["content"]["text"]
        self.assertIn("gauge", text)
        self.assertIn("tile", text)
        self.assertIn("sensor.kitchen_temperature", text)

    def test_missing_dashboard_or_entity_raises_key_error(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown dashboard"):
            self.registry.get("dashboard.review", {"dashboard_id": "missing"})

        with self.assertRaisesRegex(KeyError, "unknown entity"):
            self.registry.get(
                "dashboard.entity_card_mapping",
                {"entity_id": "sensor.missing"},
            )
