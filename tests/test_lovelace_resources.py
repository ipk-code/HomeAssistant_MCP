"""Tests for Lovelace resource discovery."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.lovelace_resources import (
    LovelaceResourceProvider,
)


class _FakeResources:
    loaded = True

    def __init__(self, items):
        self._items = items

    def async_items(self):
        return list(self._items)


class _FakeLovelaceData:
    def __init__(self, *, resource_mode, resources):
        self.resource_mode = resource_mode
        self.resources = resources


class LovelaceResourceProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        self.hass = type(
            "FakeHass",
            (),
            {
                "data": {
                    LOVELACE_DATA: _FakeLovelaceData(
                        resource_mode="storage",
                        resources=_FakeResources(
                            [
                                {
                                    "id": "abc123",
                                    "type": "module",
                                    "url": "/hacsfiles/energy-flow.js?token=secret",
                                },
                                {
                                    "type": "js",
                                    "url": "/local/custom.js?api_key=sensitive",
                                },
                            ]
                        ),
                    )
                }
            },
        )()
        self.provider = LovelaceResourceProvider(self.hass)

    async def test_list_resources_returns_storage_and_synthetic_ids(self) -> None:
        payload = await self.provider.list_resources(limit=10)
        self.assertEqual(payload["resource_mode"], "storage")
        self.assertFalse(payload["truncated"])
        self.assertEqual(payload["resources"][0]["resource_id"], "abc123")
        self.assertEqual(payload["resources"][0]["id_kind"], "storage")
        self.assertEqual(payload["resources"][1]["id_kind"], "synthetic")
        self.assertEqual(payload["resources"][1]["resource_id"][:5], "yaml-")

    async def test_urls_are_sanitized_before_exposure(self) -> None:
        payload = await self.provider.list_resources(limit=10)
        self.assertIn("token=%5Bredacted%5D", payload["resources"][0]["url"])
        self.assertIn("api_key=%5Bredacted%5D", payload["resources"][1]["url"])

    async def test_get_resource_returns_one_resource(self) -> None:
        resource = await self.provider.get_resource("abc123")
        self.assertEqual(resource["type"], "module")

        with self.assertRaisesRegex(KeyError, "unknown lovelace resource"):
            await self.provider.get_resource("missing")
