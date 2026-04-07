"""Tests for package metadata consistency."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest

from custom_components.homeassistant_mcp.const import INTEGRATION_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "homeassistant_mcp" / "manifest.json"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


class MetadataTests(unittest.TestCase):
    def test_versions_are_kept_in_sync(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["version"], INTEGRATION_VERSION)
        self.assertEqual(pyproject["project"]["version"], INTEGRATION_VERSION)
