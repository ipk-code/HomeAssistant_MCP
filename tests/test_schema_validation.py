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

    def test_validate_dashboard_one_of_allows_patch_variant(self) -> None:
        self.validator.validate_tool_arguments(
            "lovelace.validate_dashboard",
            {
                "dashboard_id": "main",
                "operations": [
                    {
                        "op": "replace",
                        "path": "/metadata/title",
                        "value": "Renamed Main",
                    }
                ],
            },
        )

    def test_accepts_valid_hass_discovery_payloads(self) -> None:
        self.validator.validate_tool_arguments(
            "hass.list_entities",
            {"domain": "light", "limit": 25},
        )
        self.validator.validate_tool_arguments(
            "hass.search_entities",
            {"query": "kitchen", "device_class": "temperature", "limit": 10},
        )
        self.validator.validate_tool_arguments(
            "hass.list_lovelace_dashboards",
            {"limit": 10},
        )
        self.validator.validate_tool_arguments(
            "hass.get_lovelace_dashboard",
            {"url_path": "pv-energy"},
        )
        self.validator.validate_tool_arguments(
            "hass.create_lovelace_dashboard",
            {
                "title": "PV Preview",
                "url_path": "pv-preview",
                "config": {"views": []},
            },
        )
        self.validator.validate_tool_arguments(
            "hass.update_lovelace_dashboard_metadata",
            {"url_path": "pv-preview", "show_in_sidebar": False},
        )
        self.validator.validate_tool_arguments(
            "hass.save_lovelace_dashboard_config",
            {"url_path": "pv-preview", "config": {"views": []}},
        )
        self.validator.validate_tool_arguments(
            "hass.delete_lovelace_dashboard",
            {"url_path": "pv-preview"},
        )
        self.validator.validate_tool_arguments(
            "hass.list_lovelace_resources",
            {"limit": 10},
        )
        self.validator.validate_tool_arguments(
            "hass.get_lovelace_resource",
            {"resource_id": "yaml-abc123"},
        )
        self.validator.validate_tool_arguments(
            "hass.list_frontend_panels",
            {"limit": 10},
        )
        self.validator.validate_tool_arguments(
            "hass.get_frontend_panel",
            {"url_path": "energy"},
        )

    def test_rejects_invalid_hass_discovery_payloads(self) -> None:
        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments("hass.search_entities", {"limit": 5})

        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments("hass.list_devices", {"limit": 201})

        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "hass.create_lovelace_dashboard",
                {"title": "Default Clone", "url_path": "default"},
            )

        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "hass.get_frontend_panel", {"url_path": "bad path"}
            )

        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "hass.get_lovelace_resource", {"resource_id": "bad path"}
            )

        with self.assertRaises(ToolSchemaValidationError):
            self.validator.validate_tool_arguments(
                "hass.get_lovelace_dashboard", {"url_path": "Energie"}
            )
