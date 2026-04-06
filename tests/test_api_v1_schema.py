"""Tests for the v1 MCP Lovelace tool contract."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "specs" / "lovelace_mcp_api_v1.json"


class ToolContractSchemaTests(unittest.TestCase):
    """Validate the JSON tool contract document shape."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.tools = {tool["name"]: tool for tool in cls.spec["tools"]}

    def test_top_level_metadata_is_v1_yaml_stateless(self) -> None:
        self.assertEqual(self.spec["api_version"], "1.0.0")
        self.assertEqual(self.spec["dashboard_mode"], "yaml")
        self.assertEqual(self.spec["transport"]["mode"], "streamable_http_stateless")
        self.assertFalse(self.spec["transport"]["sse_compatible"])

    def test_expected_tools_exist(self) -> None:
        expected = {
            "lovelace.list_dashboards",
            "lovelace.get_dashboard",
            "lovelace.create_dashboard",
            "lovelace.update_dashboard_metadata",
            "lovelace.delete_dashboard",
            "lovelace.list_views",
            "lovelace.get_view",
            "lovelace.create_view",
            "lovelace.update_view",
            "lovelace.delete_view",
            "lovelace.list_cards",
            "lovelace.get_card",
            "lovelace.create_card",
            "lovelace.update_card",
            "lovelace.delete_card",
            "lovelace.patch_dashboard",
            "lovelace.validate_dashboard",
        }
        self.assertEqual(set(self.tools), expected)

    def test_mutation_tools_are_flagged(self) -> None:
        for name in (
            "lovelace.create_dashboard",
            "lovelace.update_dashboard_metadata",
            "lovelace.delete_dashboard",
            "lovelace.create_view",
            "lovelace.update_view",
            "lovelace.delete_view",
            "lovelace.create_card",
            "lovelace.update_card",
            "lovelace.delete_card",
            "lovelace.patch_dashboard",
        ):
            self.assertTrue(self.tools[name]["mutation"], name)

    def test_card_helpers_are_typed_and_do_not_allow_raw_card_dicts(self) -> None:
        card_helper_input = self.spec["$defs"]["card_helper_input"]
        self.assertIn("oneOf", card_helper_input)
        self.assertNotIn("type", card_helper_input)
        self.assertEqual(len(card_helper_input["oneOf"]), 9)

    def test_dashboard_creation_rejects_file_paths(self) -> None:
        create_schema = self.tools["lovelace.create_dashboard"]["input_schema"]
        self.assertFalse(create_schema["additionalProperties"])
        self.assertNotIn("file_path", create_schema["properties"])

    def test_dashboard_metadata_mode_is_locked_to_yaml(self) -> None:
        metadata = self.spec["$defs"]["dashboard_metadata"]
        self.assertEqual(metadata["properties"]["mode"]["const"], "yaml")

    def test_json_patch_is_constrained_to_dashboard_document(self) -> None:
        pointer = self.spec["$defs"]["json_pointer"]
        self.assertEqual(pointer["pattern"], "^/(metadata|views)(/[A-Za-z0-9_~.-]+)*$")

        patch_schema = self.tools["lovelace.patch_dashboard"]["input_schema"]
        operations = patch_schema["properties"]["operations"]
        self.assertEqual(operations["minItems"], 1)
        self.assertEqual(operations["maxItems"], 200)

    def test_tap_action_urls_are_limited_to_safe_targets(self) -> None:
        safe_url = self.spec["$defs"]["safe_url"]
        self.assertEqual(safe_url["pattern"], "^(https?://[^\\s]+|/[^\\s]*)$")

        tap_action = self.spec["$defs"]["tap_action"]
        self.assertEqual(
            tap_action["properties"]["navigation_path"]["pattern"], "^/[^\\s]*$"
        )
        self.assertEqual(tap_action["properties"]["url"]["$ref"], "#/$defs/safe_url")

    def test_mutation_inputs_use_optimistic_concurrency(self) -> None:
        for name in (
            "lovelace.update_dashboard_metadata",
            "lovelace.delete_dashboard",
            "lovelace.create_view",
            "lovelace.update_view",
            "lovelace.delete_view",
            "lovelace.create_card",
            "lovelace.update_card",
            "lovelace.delete_card",
            "lovelace.patch_dashboard",
        ):
            properties = self.tools[name]["input_schema"]["properties"]
            self.assertIn("expected_version", properties, name)

    def test_validate_dashboard_supports_document_or_patch_validation(self) -> None:
        validate_schema = self.tools["lovelace.validate_dashboard"]["input_schema"]
        self.assertEqual(len(validate_schema["oneOf"]), 2)


if __name__ == "__main__":
    unittest.main()
