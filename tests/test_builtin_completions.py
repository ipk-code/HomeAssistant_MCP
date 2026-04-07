"""Tests for built-in completion providers."""

from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp.mcp.completions import (
    CompletionRegistry,
    register_builtin_completions,
)
from custom_components.homeassistant_mcp.lovelace.repository import (
    YamlDashboardRepository,
)


class _FakeDiscoveryProvider:
    def list_entity_ids(self) -> list[str]:
        return ["sensor.kitchen_temperature", "light.kitchen"]


class BuiltinCompletionTests(unittest.TestCase):
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
        self.card_id = self.repository.list_cards("main", "overview")[0]["card_id"]
        self.registry = CompletionRegistry()
        register_builtin_completions(
            self.registry,
            repository=self.repository,
            discovery=_FakeDiscoveryProvider(),
        )

    def test_entity_and_dashboard_completions_are_prefix_filtered(self) -> None:
        self.assertEqual(
            self.registry.complete({}, {"name": "entity_id", "value": "sensor.k"})[
                "values"
            ],
            ["sensor.kitchen_temperature"],
        )
        self.assertEqual(
            self.registry.complete({}, {"name": "dashboard_id", "value": "ma"})[
                "values"
            ],
            ["main"],
        )

    def test_view_and_card_completions_use_ref_arguments(self) -> None:
        view_values = self.registry.complete(
            {"name": "lovelace.get_view", "arguments": {"dashboard_id": "main"}},
            {"name": "view_id", "value": "ov"},
        )["values"]
        self.assertEqual(view_values, ["overview"])

        card_values = self.registry.complete(
            {
                "name": "lovelace.get_card",
                "arguments": {"dashboard_id": "main", "view_id": "overview"},
            },
            {"name": "card_id", "value": self.card_id[:8]},
        )["values"]
        self.assertEqual(card_values, [self.card_id])

    def test_icon_completion_returns_curated_matches(self) -> None:
        self.assertEqual(
            self.registry.complete({}, {"name": "icon", "value": "mdi:th"})["values"],
            ["mdi:thermometer"],
        )

    def test_missing_context_returns_empty_view_and_card_completions(self) -> None:
        self.assertEqual(
            self.registry.complete({}, {"name": "view_id", "value": "ov"}),
            {"values": [], "hasMore": False},
        )
        self.assertEqual(
            self.registry.complete(
                {"name": "lovelace.get_card", "arguments": {"dashboard_id": "missing"}},
                {"name": "card_id", "value": "heading"},
            ),
            {"values": [], "hasMore": False},
        )
