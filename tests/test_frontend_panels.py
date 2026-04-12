"""Tests for frontend panel discovery."""

from __future__ import annotations

import unittest

from custom_components.homeassistant_mcp.frontend_panels import FrontendPanelProvider


class _FakePanel:
    def __init__(
        self,
        *,
        component_name,
        title,
        icon,
        url_path,
        config=None,
        require_admin=False,
        config_panel_domain=None,
        show_in_sidebar=True,
    ):
        self.component_name = component_name
        self.sidebar_title = title
        self.sidebar_icon = icon
        self.frontend_url_path = url_path
        self.config = config
        self.require_admin = require_admin
        self.config_panel_domain = config_panel_domain
        self.sidebar_default_visible = show_in_sidebar

    def to_response(self):
        return {
            "component_name": self.component_name,
            "icon": self.sidebar_icon,
            "title": self.sidebar_title,
            "default_visible": self.sidebar_default_visible,
            "config": self.config,
            "url_path": self.frontend_url_path,
            "require_admin": self.require_admin,
            "config_panel_domain": self.config_panel_domain,
            "show_in_sidebar": self.sidebar_default_visible,
        }


class _FakeAdminUser:
    is_admin = True


class _FakeUser:
    is_admin = False


class FrontendPanelProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        from homeassistant.components.frontend import DATA_PANELS

        self.hass = type(
            "FakeHass",
            (),
            {
                "data": {
                    DATA_PANELS: {
                        "energy": _FakePanel(
                            component_name="energy",
                            title="energy",
                            icon="mdi:lightning-bolt",
                            url_path="energy",
                            config=None,
                        ),
                        "hacs": _FakePanel(
                            component_name="custom",
                            title="HACS",
                            icon="hacs:hacs",
                            url_path="hacs",
                            require_admin=True,
                            config={
                                "_panel_custom": {
                                    "name": "hacs-frontend",
                                    "js_url": "/hacsfiles/frontend.js",
                                    "token": "secret-token",
                                }
                            },
                        ),
                        "pv-energy": _FakePanel(
                            component_name="lovelace",
                            title="PV Energy",
                            icon="mdi:solar-power",
                            url_path="pv-energy",
                            config={"mode": "storage"},
                        ),
                    }
                }
            },
        )()
        self.provider = FrontendPanelProvider(self.hass)

    def test_list_panels_filters_admin_only_panels_for_non_admin_user(self) -> None:
        payload = self.provider.list_panels(user=_FakeUser(), limit=10)
        self.assertFalse(payload["truncated"])
        self.assertEqual(
            [item["url_path"] for item in payload["panels"]],
            ["energy", "pv-energy"],
        )

    def test_list_panels_includes_admin_panels_for_admin_user(self) -> None:
        payload = self.provider.list_panels(user=_FakeAdminUser(), limit=10)
        self.assertEqual(
            [item["url_path"] for item in payload["panels"]],
            ["energy", "hacs", "pv-energy"],
        )

    def test_get_panel_classifies_and_sanitizes_custom_panel_config(self) -> None:
        panel = self.provider.get_panel("hacs", user=_FakeAdminUser())
        self.assertEqual(panel["panel_kind"], "custom_panel")
        self.assertEqual(panel["source"], "home_assistant_frontend")
        self.assertEqual(
            panel["config"]["_panel_custom"]["token"],
            "[redacted]",
        )

    def test_lovelace_panel_is_classified_as_lovelace(self) -> None:
        panel = self.provider.get_panel("pv-energy", user=_FakeUser())
        self.assertEqual(panel["panel_kind"], "lovelace")
        self.assertEqual(panel["config"], {"mode": "storage"})

    def test_unknown_or_hidden_panel_raises_key_error(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown frontend panel"):
            self.provider.get_panel("missing", user=_FakeUser())

        with self.assertRaisesRegex(KeyError, "unknown frontend panel"):
            self.provider.get_panel("hacs", user=_FakeUser())
