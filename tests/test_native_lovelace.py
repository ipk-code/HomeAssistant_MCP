"""Tests for native Home Assistant Lovelace dashboard access."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.native_lovelace import NativeLovelaceProvider


class _FakeLovelaceConfig:
    def __init__(self, *, url_path, config, info):
        self.url_path = url_path
        self.config = config
        self._info = info

    async def async_get_info(self):
        return self._info

    async def async_load(self, force):
        return {"views": [{"title": "Overview"}]}


class _FakeLovelaceData:
    def __init__(self, dashboards):
        self.dashboards = dashboards


class NativeLovelaceProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        default = _FakeLovelaceConfig(
            url_path=None,
            config={"title": "Default", "show_in_sidebar": True},
            info={"mode": "storage", "views": 1},
        )
        pv = _FakeLovelaceConfig(
            url_path="pv-energy",
            config={
                "id": "pv_energy",
                "title": "Photovoltaik",
                "show_in_sidebar": True,
                "icon": "mdi:solar-power",
            },
            info={"mode": "storage", "views": 2},
        )

        self.hass = type(
            "FakeHass",
            (),
            {
                "data": {
                    LOVELACE_DATA: _FakeLovelaceData({None: default, "pv-energy": pv})
                }
            },
        )()
        self.provider = NativeLovelaceProvider(self.hass)

    async def test_list_dashboards_returns_default_and_named_dashboards(self) -> None:
        payload = await self.provider.list_dashboards(limit=10)
        self.assertFalse(payload["truncated"])
        self.assertEqual(
            [item["url_path"] for item in payload["dashboards"]],
            ["default", "pv-energy"],
        )
        self.assertEqual(payload["dashboards"][1]["id"], "pv_energy")

    async def test_get_dashboard_resolves_default_alias_and_named_dashboard(
        self,
    ) -> None:
        default = await self.provider.get_dashboard("default")
        self.assertEqual(default["metadata"]["url_path"], "default")

        named = await self.provider.get_dashboard("pv-energy")
        self.assertEqual(named["metadata"]["id"], "pv_energy")

    async def test_unknown_dashboard_raises_key_error(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown lovelace dashboard"):
            await self.provider.get_dashboard("missing")
