"""Tests for typed card helper normalization and rendering."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.lovelace.card_helpers import (
    normalize_card_helper,
    render_card_config,
)
from custom_components.homeassistant_mcp.lovelace.errors import DashboardValidationError


class CardHelperTests(unittest.TestCase):
    def test_tile_card_round_trip_shape(self) -> None:
        card = normalize_card_helper(
            {
                "kind": "tile",
                "entity_id": "light.kitchen",
                "title": "Kitchen Light",
                "tap_action": {"action": "navigate", "navigation_path": "/lovelace/kitchen"},
            }
        )

        self.assertEqual(card["kind"], "tile")
        self.assertIn("card_id", card)
        self.assertEqual(card["entity_id"], "light.kitchen")

        rendered = render_card_config(card)
        self.assertEqual(
            rendered,
            {
                "type": "tile",
                "entity": "light.kitchen",
                "name": "Kitchen Light",
                "tap_action": {"action": "navigate", "navigation_path": "/lovelace/kitchen"},
            },
        )

    def test_nested_grid_card_renders_nested_lovelace_cards(self) -> None:
        card = normalize_card_helper(
            {
                "kind": "grid",
                "columns": 2,
                "cards": [
                    {"kind": "heading", "title": "Room"},
                    {"kind": "markdown", "content": "Status"},
                ],
            }
        )

        rendered = render_card_config(card)
        self.assertEqual(rendered["type"], "grid")
        self.assertEqual(rendered["columns"], 2)
        self.assertEqual(rendered["cards"][0]["type"], "heading")
        self.assertEqual(rendered["cards"][1]["type"], "markdown")

    def test_unsafe_url_is_rejected(self) -> None:
        with self.assertRaises(DashboardValidationError):
            normalize_card_helper(
                {
                    "kind": "tile",
                    "entity_id": "light.kitchen",
                    "tap_action": {"action": "url", "url": "javascript:alert(1)"},
                }
            )

    def test_entities_card_requires_entities(self) -> None:
        with self.assertRaises(DashboardValidationError):
            normalize_card_helper({"kind": "entities", "entities": []})

    def test_unknown_card_fields_are_rejected(self) -> None:
        with self.assertRaises(DashboardValidationError):
            normalize_card_helper(
                {"kind": "tile", "entity_id": "light.kitchen", "custom": "value"}
            )

    def test_markdown_content_supports_longer_content_than_title_fields(self) -> None:
        content = "x" * 1024
        card = normalize_card_helper({"kind": "markdown", "content": content})
        self.assertEqual(card["content"], content)

    def test_deeply_nested_cards_are_rejected(self) -> None:
        """CWE-400: Adversarially deep nesting must not cause a stack overflow."""
        from custom_components.homeassistant_mcp.lovelace.card_helpers import (
            MAX_CARD_NESTING_DEPTH,
        )

        def make_nested(depth: int) -> dict:
            if depth == 0:
                return {"kind": "tile", "entity_id": "light.test"}
            return {"kind": "horizontal_stack", "cards": [make_nested(depth - 1)]}

        # One level beyond the limit must raise, not recurse indefinitely
        with self.assertRaises(DashboardValidationError):
            normalize_card_helper(make_nested(MAX_CARD_NESTING_DEPTH + 2))

    def test_nesting_at_max_depth_is_accepted(self) -> None:
        """Cards nested exactly at the limit must be accepted."""
        from custom_components.homeassistant_mcp.lovelace.card_helpers import (
            MAX_CARD_NESTING_DEPTH,
        )

        def make_nested(depth: int) -> dict:
            if depth == 0:
                return {"kind": "tile", "entity_id": "light.test"}
            return {"kind": "horizontal_stack", "cards": [make_nested(depth - 1)]}

        card = normalize_card_helper(make_nested(MAX_CARD_NESTING_DEPTH))
        self.assertEqual(card["kind"], "horizontal_stack")

    def test_auto_generated_card_ids_are_unique_across_calls(self) -> None:
        """CWE-330: Auto-generated card IDs must not collide."""
        ids = {
            normalize_card_helper({"kind": "tile", "entity_id": "light.x"})["card_id"]
            for _ in range(50)
        }
        self.assertEqual(len(ids), 50, "All generated card IDs must be unique")

    def test_auto_generated_card_id_matches_expected_format(self) -> None:
        """Generated IDs must pass the card_id validator (card:<hex>)."""
        card = normalize_card_helper({"kind": "tile", "entity_id": "light.x"})
        card_id = card["card_id"]
        self.assertTrue(card_id.startswith("card:"), f"Expected 'card:' prefix, got {card_id!r}")
        hex_part = card_id[len("card:"):]
        self.assertTrue(all(c in "0123456789abcdef" for c in hex_part), f"Non-hex chars in {hex_part!r}")
