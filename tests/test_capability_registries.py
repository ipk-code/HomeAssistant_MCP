"""Tests for MCP capability registries."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.mcp.completions import (
    CompletionRegistry,
    MAX_COMPLETION_VALUES,
)
from custom_components.homeassistant_mcp.mcp.prompts import (
    PromptArgument,
    PromptDefinition,
    PromptRegistry,
)
from custom_components.homeassistant_mcp.mcp.resources import (
    ResourceDefinition,
    ResourceRegistry,
    ResourceTemplateDefinition,
)


class ResourceRegistryTests(unittest.TestCase):
    def test_resource_registry_lists_resources_and_templates(self) -> None:
        registry = ResourceRegistry()
        registry.register(
            ResourceDefinition(
                uri="hass://config",
                name="Config",
                description="Configuration",
                mime_type="application/json",
            ),
            lambda: [
                {"uri": "hass://config", "mimeType": "application/json", "text": "{}"}
            ],
        )
        registry.register_template(
            ResourceTemplateDefinition(
                uri_template="hass://dashboard/{dashboard_id}",
                name="Dashboard",
                description="Dashboard template",
                mime_type="application/json",
            ),
            lambda params, uri: [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": params["dashboard_id"],
                }
            ],
        )

        payload = registry.list_payload()
        self.assertEqual(payload["resources"][0]["uri"], "hass://config")
        self.assertEqual(
            payload["resourceTemplates"][0]["uriTemplate"],
            "hass://dashboard/{dashboard_id}",
        )
        self.assertEqual(registry.read("hass://config")[0]["text"], "{}")
        self.assertEqual(
            registry.read("hass://dashboard/main")[0]["text"],
            "main",
        )

    def test_resource_registry_rejects_unknown_uri(self) -> None:
        registry = ResourceRegistry()
        with self.assertRaisesRegex(KeyError, "unknown resource"):
            registry.read("hass://missing")


class PromptRegistryTests(unittest.TestCase):
    def test_prompt_registry_lists_and_dispatches_prompts(self) -> None:
        registry = PromptRegistry()
        registry.register(
            PromptDefinition(
                name="dashboard.review",
                description="Review",
                arguments=(
                    PromptArgument(
                        name="dashboard_id",
                        description="Dashboard",
                        required=True,
                    ),
                ),
            ),
            lambda arguments: {"description": arguments["dashboard_id"]},
        )

        self.assertEqual(registry.list_prompts()[0]["name"], "dashboard.review")
        self.assertEqual(
            registry.get("dashboard.review", {"dashboard_id": "main"})["description"],
            "main",
        )

    def test_prompt_registry_rejects_unknown_prompt(self) -> None:
        registry = PromptRegistry()
        with self.assertRaisesRegex(KeyError, "unknown prompt"):
            registry.get("missing", {})


class CompletionRegistryTests(unittest.TestCase):
    def test_completion_registry_dispatches_specific_and_fallback_providers(
        self,
    ) -> None:
        registry = CompletionRegistry()
        registry.register(
            ref_name="dashboard.review",
            argument_name="dashboard_id",
            provider=lambda ref, argument: {"values": ["main"], "hasMore": False},
        )
        registry.register(
            argument_name="entity_id",
            provider=lambda ref, argument: {
                "values": ["light.kitchen"],
                "hasMore": False,
            },
        )

        self.assertEqual(
            registry.complete(
                {"name": "dashboard.review"},
                {"name": "dashboard_id", "value": "m"},
            )["values"],
            ["main"],
        )
        self.assertEqual(
            registry.complete(
                {"name": "dashboard.other"},
                {"name": "entity_id", "value": "light."},
            )["values"],
            ["light.kitchen"],
        )

    def test_completion_registry_returns_empty_result_without_provider(self) -> None:
        registry = CompletionRegistry()
        self.assertEqual(
            registry.complete({"name": "dashboard.review"}, {"name": "dashboard_id"}),
            {"values": [], "hasMore": False},
        )

    def test_completion_registry_normalizes_duplicates_and_caps_values(self) -> None:
        registry = CompletionRegistry()
        registry.register(
            argument_name="entity_id",
            provider=lambda ref, argument: {
                "values": ["sensor.duplicate", "sensor.duplicate"]
                + [
                    f"sensor.item_{index}" for index in range(MAX_COMPLETION_VALUES + 2)
                ],
                "hasMore": False,
            },
        )

        result = registry.complete(
            {"name": "dashboard.review"},
            {"name": "entity_id", "value": "sensor."},
        )
        self.assertEqual(len(result["values"]), MAX_COMPLETION_VALUES)
        self.assertEqual(result["values"][0], "sensor.duplicate")
        self.assertTrue(result["hasMore"])
