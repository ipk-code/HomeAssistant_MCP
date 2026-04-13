"""Tests for the template sensor provider sanitization helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from custom_components.homeassistant_mcp.template_sensors import TemplateSensorProvider


class SanitizeJsonTests(unittest.TestCase):
    """Unit tests for TemplateSensorProvider._sanitize_json."""

    def setUp(self) -> None:
        self.provider = TemplateSensorProvider.__new__(TemplateSensorProvider)

    def test_nan_is_converted_to_none(self) -> None:
        """CWE-20: NaN must not leak into JSON responses."""
        self.assertIsNone(self.provider._sanitize_json(float("nan")))

    def test_infinity_is_converted_to_none(self) -> None:
        """CWE-20: Infinity must not leak into JSON responses."""
        self.assertIsNone(self.provider._sanitize_json(float("inf")))
        self.assertIsNone(self.provider._sanitize_json(float("-inf")))

    def test_finite_floats_pass_through(self) -> None:
        self.assertEqual(self.provider._sanitize_json(3.14), 3.14)
        self.assertEqual(self.provider._sanitize_json(0.0), 0.0)
        self.assertEqual(self.provider._sanitize_json(-1.5), -1.5)

    def test_nested_nan_is_sanitized(self) -> None:
        """CWE-20: NaN buried in nested structures must be caught."""
        result = self.provider._sanitize_json(
            {"outer": {"inner": float("nan"), "ok": 1}}
        )
        self.assertIsNone(result["outer"]["inner"])
        self.assertEqual(result["outer"]["ok"], 1)

    def test_nan_in_list_is_sanitized(self) -> None:
        result = self.provider._sanitize_json([1, float("inf"), "a"])
        self.assertEqual(result, [1, None, "a"])

    def test_primitives_pass_through(self) -> None:
        self.assertIsNone(self.provider._sanitize_json(None))
        self.assertEqual(self.provider._sanitize_json("hello"), "hello")
        self.assertEqual(self.provider._sanitize_json(42), 42)
        self.assertTrue(self.provider._sanitize_json(True))
