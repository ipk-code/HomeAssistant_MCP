"""Tests for restricted dashboard JSON Patch support."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.lovelace.errors import PatchApplicationError
from custom_components.homeassistant_mcp.lovelace.patch import apply_json_patch


class PatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = {
            "metadata": {"title": "Main", "dashboard_id": "main", "url_path": "main", "mode": "yaml", "show_in_sidebar": True, "require_admin": False},
            "views": [
                {"view_id": "overview", "title": "Overview", "path": "overview", "cards": []}
            ],
            "dashboard_version": 0,
        }

    def test_add_view_with_json_patch(self) -> None:
        patched, applied = apply_json_patch(
            self.document,
            [
                {
                    "op": "add",
                    "path": "/views/1",
                    "value": {"view_id": "climate", "title": "Climate", "path": "climate", "cards": []},
                }
            ],
        )
        self.assertEqual(applied, 1)
        self.assertEqual(len(patched["views"]), 2)
        self.assertEqual(patched["views"][1]["view_id"], "climate")

    def test_replace_metadata_field(self) -> None:
        patched, _ = apply_json_patch(
            self.document,
            [{"op": "replace", "path": "/metadata/title", "value": "Updated"}],
        )
        self.assertEqual(patched["metadata"]["title"], "Updated")

    def test_copy_and_move_operations(self) -> None:
        document = {
            **self.document,
            "views": [
                {"view_id": "overview", "title": "Overview", "path": "overview", "cards": [{"card_id": "card:1", "kind": "heading", "title": "A"}]},
                {"view_id": "other", "title": "Other", "path": "other", "cards": []},
            ],
        }
        patched, applied = apply_json_patch(
            document,
            [
                {"op": "copy", "from": "/views/0/cards/0", "path": "/views/1/cards/0"},
                {"op": "move", "from": "/views/1/cards/0", "path": "/views/0/cards/1"},
            ],
        )
        self.assertEqual(applied, 2)
        self.assertEqual(len(patched["views"][0]["cards"]), 2)
        self.assertEqual(patched["views"][1]["cards"], [])

    def test_patch_rejects_out_of_scope_paths(self) -> None:
        with self.assertRaises(PatchApplicationError):
            apply_json_patch(self.document, [{"op": "replace", "path": "/dashboard_version", "value": 1}])

    def test_patch_test_operation_fails_when_values_differ(self) -> None:
        with self.assertRaises(PatchApplicationError):
            apply_json_patch(self.document, [{"op": "test", "path": "/metadata/title", "value": "Nope"}])

    def test_patch_rejects_immutable_identity_fields(self) -> None:
        with self.assertRaises(PatchApplicationError):
            apply_json_patch(
                self.document,
                [{"op": "replace", "path": "/metadata/dashboard_id", "value": "other"}],
            )
