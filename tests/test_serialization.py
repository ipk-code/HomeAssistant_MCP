"""Tests for YAML serialization helpers."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.lovelace.serialization import dump_yaml


class SerializationTests(unittest.TestCase):
    def test_dump_yaml_renders_nested_block_style_yaml(self) -> None:
        rendered = dump_yaml(
            {
                "title": "Main Dashboard",
                "views": [
                    {
                        "title": "Overview",
                        "path": "overview",
                        "cards": [
                            {"type": "tile", "entity": "light.kitchen"},
                            {"type": "markdown", "content": "Hello\nWorld"},
                        ],
                    }
                ],
            }
        )

        self.assertIn("title: 'Main Dashboard'\n", rendered)
        self.assertIn("views:\n", rendered)
        self.assertIn("  -\n", rendered)
        self.assertIn("      type: markdown\n", rendered)
        self.assertIn("      content: |-\n", rendered)
        self.assertIn("        Hello\n", rendered)
        self.assertNotIn("{", rendered)

    def test_dump_yaml_quotes_reserved_scalars(self) -> None:
        rendered = dump_yaml({"value": "true", "icon": "mdi:home"})
        self.assertIn("value: 'true'\n", rendered)
        self.assertIn("icon: 'mdi:home'\n", rendered)
