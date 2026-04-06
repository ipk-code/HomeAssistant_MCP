"""Tests for spec-driven MCP tool argument validation."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.mcp.schema import (
    ToolSchemaValidationError,
    ToolSchemaValidator,
)
from custom_components.homeassistant_mcp.mcp.server import load_api_contract


class SchemaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec, _ = load_api_contract()
        cls.validator = ToolSchemaValidator(spec)

    def test_accepts_valid_create_dashboard_payload(self) -> None:
        self.validator.validate_tool_arguments(
            "lovelace.create_dashboard",
            {
                "dashboard_id": "main",
                "title": "Main",
                "url_path": "main",
                "views": [],
            },
        )

    def test_rejects_missing_required_fields(self) -> None:
        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "lovelace.create_dashboard",
                {"dashboard_id": "main", "url_path": "main"},
            )

    def test_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "lovelace.create_dashboard",
                {
                    "dashboard_id": "main",
                    "title": "Main",
                    "url_path": "main",
                    "views": [],
                    "file_path": "../evil.yaml",
                },
            )

    def test_rejects_invalid_nested_card_shape(self) -> None:
        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "lovelace.create_card",
                {
                    "dashboard_id": "main",
                    "view_id": "overview",
                    "card": {"kind": "tile", "entity_id": 7},
                },
            )

    def test_validate_dashboard_one_of_allows_document_variant(self) -> None:
        self.validator.validate_tool_arguments(
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
