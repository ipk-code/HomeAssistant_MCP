"""Tests for the YAML dashboard repository."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from custom_components.homeassistant_mcp.lovelace.errors import (
    DashboardConflictError,
    DashboardValidationError,
)
from custom_components.homeassistant_mcp.lovelace.repository import YamlDashboardRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.repository = YamlDashboardRepository(self.tempdir.name)

    def _create_dashboard(self) -> dict:
        return self.repository.create_dashboard(
            {
                "dashboard_id": "main",
                "title": "Main Dashboard",
                "url_path": "main",
                "views": [
                    {
                        "view_id": "overview",
                        "title": "Overview",
                        "path": "overview",
                        "cards": [{"kind": "heading", "title": "Welcome"}],
                    }
                ],
            }
        )

    def test_create_dashboard_writes_managed_and_rendered_files(self) -> None:
        created = self._create_dashboard()
        self.assertEqual(created["metadata"]["dashboard_id"], "main")
        self.assertEqual(created["dashboard_version"], 0)

        managed = Path(self.tempdir.name) / "managed" / "main.json"
        rendered = Path(self.tempdir.name) / "rendered" / "main.yaml"
        self.assertTrue(managed.exists())
        self.assertTrue(rendered.exists())

        rendered_payload = rendered.read_text(encoding="utf-8")
        self.assertIn("title: 'Main Dashboard'\n", rendered_payload)
        self.assertIn("views:\n", rendered_payload)
        self.assertIn("      type: heading\n", rendered_payload)
        self.assertNotIn("{", rendered_payload)

    def test_list_and_get_dashboard(self) -> None:
        self._create_dashboard()
        listed = self.repository.list_dashboards()
        loaded = self.repository.get_dashboard("main")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["title"], "Main Dashboard")
        self.assertEqual(loaded["metadata"]["url_path"], "main")

    def test_metadata_update_enforces_expected_version(self) -> None:
        self._create_dashboard()
        with self.assertRaises(DashboardConflictError):
            self.repository.update_dashboard_metadata(
                "main", {"title": "New"}, expected_version=1
            )

        updated = self.repository.update_dashboard_metadata(
            "main", {"title": "New"}, expected_version=0
        )
        self.assertEqual(updated["metadata"]["title"], "New")
        self.assertEqual(updated["dashboard_version"], 1)

    def test_view_crud(self) -> None:
        self._create_dashboard()
        view, version = self.repository.create_view(
            "main",
            {"view_id": "climate", "title": "Climate", "path": "climate", "cards": []},
            expected_version=0,
        )
        self.assertEqual(view["view_id"], "climate")
        self.assertEqual(version, 1)

        updated, version = self.repository.update_view(
            "main",
            "climate",
            {"view_id": "climate", "title": "HVAC", "path": "climate", "cards": []},
            expected_version=1,
            position=0,
        )
        self.assertEqual(updated["title"], "HVAC")
        self.assertEqual(version, 2)
        self.assertEqual(self.repository.list_views("main")[0]["view_id"], "climate")

        deleted = self.repository.delete_view("main", "climate", expected_version=2)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(deleted["dashboard_version"], 3)

    def test_card_crud(self) -> None:
        self._create_dashboard()
        card, version = self.repository.create_card(
            "main",
            "overview",
            {"kind": "tile", "entity_id": "light.kitchen", "title": "Kitchen"},
            expected_version=0,
        )
        self.assertEqual(card["kind"], "tile")
        self.assertEqual(version, 1)

        updated, version = self.repository.update_card(
            "main",
            "overview",
            card["card_id"],
            {"kind": "markdown", "content": "Hello"},
            expected_version=1,
        )
        self.assertEqual(updated["kind"], "markdown")
        self.assertEqual(updated["card_id"], card["card_id"])
        self.assertEqual(version, 2)

        deleted = self.repository.delete_card(
            "main", "overview", card["card_id"], expected_version=2
        )
        self.assertTrue(deleted["deleted"])
        self.assertEqual(deleted["dashboard_version"], 3)

    def test_patch_dashboard_revalidates_document(self) -> None:
        self._create_dashboard()
        dashboard, applied = self.repository.patch_dashboard(
            "main",
            [
                {"op": "replace", "path": "/metadata/title", "value": "Updated"},
                {
                    "op": "add",
                    "path": "/views/1",
                    "value": {"view_id": "lights", "title": "Lights", "path": "lights", "cards": []},
                },
            ],
            expected_version=0,
        )
        self.assertEqual(applied, 2)
        self.assertEqual(dashboard["metadata"]["title"], "Updated")
        self.assertEqual(dashboard["dashboard_version"], 1)
        self.assertEqual(len(dashboard["views"]), 2)

    def test_reserved_url_path_is_rejected(self) -> None:
        with self.assertRaises(DashboardValidationError):
            self.repository.create_dashboard(
                {"dashboard_id": "main", "title": "Main", "url_path": "api", "views": []}
            )

    def test_dashboard_payload_rejects_unknown_fields(self) -> None:
        with self.assertRaises(DashboardValidationError):
            self.repository.create_dashboard(
                {
                    "dashboard_id": "main",
                    "title": "Main",
                    "url_path": "main",
                    "views": [],
                    "file_path": "../evil.yaml",
                }
            )

    def test_non_boolean_sidebar_value_is_rejected(self) -> None:
        with self.assertRaises(DashboardValidationError):
            self.repository.create_dashboard(
                {
                    "dashboard_id": "main",
                    "title": "Main",
                    "url_path": "main",
                    "show_in_sidebar": "yes",
                    "views": [],
                }
            )

    def test_atomic_write_cleans_up_temp_file_on_failure(self) -> None:
        temp_dir = Path(self.tempdir.name)
        target = temp_dir / "managed" / "main.json"

        with patch.object(Path, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.repository._write_text_atomically(target, "payload")

        leftovers = list((temp_dir / "managed").glob(".*.tmp"))
        self.assertEqual(leftovers, [])

    def test_create_view_rejects_when_dashboard_is_full(self) -> None:
        """CWE-400: Adding views beyond MAX_VIEWS_PER_DASHBOARD must be rejected."""
        from custom_components.homeassistant_mcp.lovelace.repository import MAX_VIEWS_PER_DASHBOARD

        self.repository.create_dashboard(
            {"dashboard_id": "big", "title": "Big", "url_path": "big", "views": []}
        )
        for i in range(MAX_VIEWS_PER_DASHBOARD):
            self.repository.create_view(
                "big", {"view_id": f"view{i}", "title": f"V{i}", "path": f"v{i}", "cards": []}
            )
        with self.assertRaises(DashboardValidationError):
            self.repository.create_view(
                "big", {"view_id": "overflow", "title": "Over", "path": "overflow", "cards": []}
            )

    def test_create_card_rejects_when_view_is_full(self) -> None:
        """CWE-400: Adding cards beyond MAX_CARDS_PER_VIEW must be rejected."""
        from custom_components.homeassistant_mcp.lovelace.repository import MAX_CARDS_PER_VIEW

        self.repository.create_dashboard(
            {"dashboard_id": "d2", "title": "D2", "url_path": "d2", "views": []}
        )
        self.repository.create_view(
            "d2", {"view_id": "v1", "title": "V1", "path": "v1", "cards": []}
        )
        for _ in range(MAX_CARDS_PER_VIEW):
            self.repository.create_card(
                "d2", "v1", {"kind": "tile", "entity_id": "light.test"}
            )
        with self.assertRaises(DashboardValidationError):
            self.repository.create_card(
                "d2", "v1", {"kind": "tile", "entity_id": "light.overflow"}
            )

    def test_storage_directories_have_owner_only_permissions(self) -> None:
        """CWE-732: Storage directories must be created with owner-only permissions."""
        import stat

        managed = Path(self.tempdir.name) / "managed"
        rendered = Path(self.tempdir.name) / "rendered"
        for directory in (managed, rendered):
            mode = directory.stat().st_mode & 0o777
            self.assertEqual(
                mode,
                stat.S_IRWXU,
                f"{directory.name} directory has mode {oct(mode)}, expected {oct(stat.S_IRWXU)}",
            )
