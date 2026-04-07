"""Tests for package metadata consistency."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest

from custom_components.homeassistant_mcp.const import (
    DEFAULT_TRANSPORT,
    INTEGRATION_VERSION,
    STREAMABLE_HTTP_API,
)
from custom_components.homeassistant_mcp.http import HomeAssistantMCPStreamableView
from custom_components.homeassistant_mcp.mcp.server import load_api_contract

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "homeassistant_mcp" / "manifest.json"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
README_PATH = REPO_ROOT / "README.md"
INSTALL_GUIDE_PATH = REPO_ROOT / "docs" / "guides" / "home-assistant-installation.md"
DOCS_INDEX_PATH = REPO_ROOT / "docs" / "README.md"
OVERVIEW_PATH = REPO_ROOT / "docs" / "api" / "overview.md"
CONFIG_PATH = REPO_ROOT / "docs" / "api" / "configuration.md"
TOOLS_PATH = REPO_ROOT / "docs" / "api" / "tools.md"
OPENCODE_PATH = REPO_ROOT / "docs" / "guides" / "opencode-integration.md"


class MetadataTests(unittest.TestCase):
    def test_versions_are_kept_in_sync(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["version"], INTEGRATION_VERSION)
        self.assertEqual(pyproject["project"]["version"], INTEGRATION_VERSION)

    def test_hacs_facing_docs_show_current_version(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        install_guide = INSTALL_GUIDE_PATH.read_text(encoding="utf-8")

        self.assertIn(f"Current integration version: `{INTEGRATION_VERSION}`", readme)
        self.assertIn(
            f"Loaded Home Assistant MCP version {INTEGRATION_VERSION} entry ...",
            readme,
        )
        self.assertIn(
            f"Current integration version in this repository: `{INTEGRATION_VERSION}`",
            install_guide,
        )

    def test_docs_publish_current_endpoint_and_auth_model(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        overview = OVERVIEW_PATH.read_text(encoding="utf-8")
        config = CONFIG_PATH.read_text(encoding="utf-8")
        install_guide = INSTALL_GUIDE_PATH.read_text(encoding="utf-8")
        opencode = OPENCODE_PATH.read_text(encoding="utf-8")

        self.assertTrue(HomeAssistantMCPStreamableView.requires_auth)
        for document in (readme, overview, config, install_guide, opencode):
            self.assertIn(STREAMABLE_HTTP_API, document)

        self.assertIn(DEFAULT_TRANSPORT, readme)
        self.assertIn(DEFAULT_TRANSPORT, config)
        self.assertIn("Home Assistant auth | required", readme)
        self.assertIn("Home Assistant auth | required", config)
        self.assertIn("oauth: false", readme)
        self.assertIn("oauth: false", opencode)
        self.assertIn("Home Assistant long-lived access token", readme)
        self.assertIn("Home Assistant long-lived access token", opencode)
        self.assertIn("completion/complete", readme)
        self.assertIn("completion/complete", overview)
        self.assertIn("completion/complete", opencode)
        self.assertIn("resources/read", readme)
        self.assertIn("resources/read", overview)
        self.assertIn("resources/read", opencode)
        self.assertIn("prompts/get", readme)
        self.assertIn("prompts/get", overview)
        self.assertIn("prompts/get", opencode)

    def test_docs_publish_stable_v1_capability_summary(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        docs_index = DOCS_INDEX_PATH.read_text(encoding="utf-8")
        tools_doc = TOOLS_PATH.read_text(encoding="utf-8")
        _spec, tools = load_api_contract()

        self.assertIn("Stable in v1", readme)
        self.assertIn("Not shipped yet", readme)
        self.assertIn("## API Docs", docs_index)

        expected_tools = {
            "hass.list_entities",
            "lovelace.list_dashboards",
            "lovelace.create_dashboard",
            "lovelace.patch_dashboard",
            "lovelace.create_card",
        }
        self.assertTrue(expected_tools.issubset({tool.name for tool in tools}))
        for tool_name in expected_tools:
            self.assertIn(tool_name, readme)
            self.assertIn(tool_name, tools_doc)

        self.assertIn(
            "entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon`", readme
        )
        self.assertIn("hass://dashboard/{dashboard_id}", readme)
        self.assertIn("dashboard.review", readme)
