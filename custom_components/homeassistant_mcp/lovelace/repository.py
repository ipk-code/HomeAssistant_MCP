"""YAML dashboard repository backed by managed JSON and rendered YAML files."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from typing import Any

from .card_helpers import clone_card, normalize_card_helper, render_card_config
from .errors import (
    DashboardConflictError,
    DashboardNotFoundError,
    DashboardValidationError,
)
from .patch import apply_json_patch
from .serialization import dump_yaml
from .validation import (
    apply_metadata_patch,
    ensure_expected_version,
    ensure_integer,
    normalize_dashboard_metadata,
    reject_unknown_keys,
    validate_card_id,
    validate_dashboard_id,
    validate_view_id,
    validate_title,
    validate_url_path,
)


# CWE-400: Hard caps prevent authenticated clients from exhausting storage
# and memory by creating unboundedly large dashboard structures.
MAX_VIEWS_PER_DASHBOARD = 50
MAX_CARDS_PER_VIEW = 200

# CWE-732: Owner-only directory mode. Dashboard JSON files contain the
# full Lovelace configuration; group/world read access is unnecessary.
_DIR_MODE = stat.S_IRWXU  # 0o700


def _restrict_directory(path: Path) -> None:
    """Apply owner-only permissions to a storage directory (best-effort)."""
    try:
        path.chmod(_DIR_MODE)
    except OSError:
        # chmod may fail on some platforms or Docker volumes; do not abort.
        pass


class YamlDashboardRepository:
    """Manage canonical dashboard documents and rendered YAML dashboard files."""

    def __init__(self, root_path: str | Path) -> None:
        self._root_path = Path(root_path)
        self._managed_path = self._root_path / "managed"
        self._rendered_path = self._root_path / "rendered"
        self._managed_path.mkdir(parents=True, exist_ok=True)
        self._rendered_path.mkdir(parents=True, exist_ok=True)
        _restrict_directory(self._managed_path)
        _restrict_directory(self._rendered_path)

    def list_dashboards(self) -> list[dict[str, Any]]:
        dashboards: list[dict[str, Any]] = []
        for path in sorted(self._managed_path.glob("*.json")):
            document = self._read_document(path.stem)
            dashboards.append(deepcopy(document["metadata"]))
        return dashboards

    def get_dashboard(self, dashboard_id: str) -> dict[str, Any]:
        return self._read_document(validate_dashboard_id(dashboard_id))

    def create_dashboard(self, payload: dict[str, Any]) -> dict[str, Any]:
        reject_unknown_keys(
            payload,
            {
                "dashboard_id",
                "title",
                "url_path",
                "icon",
                "show_in_sidebar",
                "require_admin",
                "views",
            },
            "dashboard payload",
        )
        metadata = normalize_dashboard_metadata(
            {
                key: payload[key]
                for key in (
                    "dashboard_id",
                    "title",
                    "url_path",
                    "icon",
                    "show_in_sidebar",
                    "require_admin",
                )
                if key in payload
            }
        )
        dashboard_id = metadata["dashboard_id"]
        if self._document_path(dashboard_id).exists():
            raise DashboardConflictError(f"dashboard already exists: {dashboard_id}")
        views = [self._normalize_view(view) for view in payload.get("views", [])]
        self._ensure_view_uniqueness(views)
        document = {
            "metadata": metadata,
            "views": views,
            "dashboard_version": 0,
        }
        self._write_document(document)
        return deepcopy(document)

    def update_dashboard_metadata(
        self,
        dashboard_id: str,
        metadata_patch: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        document["metadata"] = apply_metadata_patch(document["metadata"], metadata_patch)
        document["dashboard_version"] += 1
        self._write_document(document)
        return deepcopy(document)

    def delete_dashboard(
        self, dashboard_id: str, *, expected_version: int | None = None
    ) -> dict[str, Any]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        self._document_path(dashboard_id).unlink(missing_ok=False)
        self._render_path(dashboard_id).unlink(missing_ok=True)
        return {"dashboard_id": dashboard_id, "deleted": True}

    def list_views(self, dashboard_id: str) -> list[dict[str, Any]]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        return [self._view_summary(view) for view in document["views"]]

    def get_view(self, dashboard_id: str, view_id: str) -> dict[str, Any]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        return deepcopy(self._find_view(document, validate_view_id(view_id)))

    def create_view(
        self,
        dashboard_id: str,
        view: dict[str, Any],
        *,
        position: int | None = None,
        expected_version: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        if len(document["views"]) >= MAX_VIEWS_PER_DASHBOARD:
            raise DashboardValidationError(
                f"dashboard already has the maximum of {MAX_VIEWS_PER_DASHBOARD} views"
            )
        normalized = self._normalize_view(view)
        if any(item["view_id"] == normalized["view_id"] for item in document["views"]):
            raise DashboardConflictError(f"view already exists: {normalized['view_id']}")
        self._insert_item(document["views"], normalized, position)
        document["dashboard_version"] += 1
        self._write_document(document)
        return deepcopy(normalized), document["dashboard_version"]

    def update_view(
        self,
        dashboard_id: str,
        view_id: str,
        view: dict[str, Any],
        *,
        position: int | None = None,
        expected_version: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        view_id = validate_view_id(view_id)
        index = self._find_view_index(document, view_id)
        normalized = self._normalize_view(view)
        if normalized["view_id"] != view_id:
            raise DashboardValidationError("view_id cannot be changed during update")
        document["views"][index] = normalized
        if position is not None:
            moved = document["views"].pop(index)
            self._insert_item(document["views"], moved, position)
        document["dashboard_version"] += 1
        self._write_document(document)
        return deepcopy(normalized), document["dashboard_version"]

    def delete_view(
        self,
        dashboard_id: str,
        view_id: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        index = self._find_view_index(document, validate_view_id(view_id))
        document["views"].pop(index)
        document["dashboard_version"] += 1
        self._write_document(document)
        return {
            "dashboard_id": dashboard_id,
            "view_id": view_id,
            "deleted": True,
            "dashboard_version": document["dashboard_version"],
        }

    def list_cards(self, dashboard_id: str, view_id: str) -> list[dict[str, Any]]:
        view = self.get_view(dashboard_id, view_id)
        return [clone_card(card) for card in view["cards"]]

    def get_card(self, dashboard_id: str, view_id: str, card_id: str) -> dict[str, Any]:
        view = self.get_view(dashboard_id, view_id)
        card_id = validate_card_id(card_id)
        for card in view["cards"]:
            if card["card_id"] == card_id:
                return clone_card(card)
        raise DashboardNotFoundError(f"card not found: {card_id}")

    def create_card(
        self,
        dashboard_id: str,
        view_id: str,
        card: dict[str, Any],
        *,
        position: int | None = None,
        expected_version: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        view = self._find_view(document, validate_view_id(view_id))
        if len(view["cards"]) >= MAX_CARDS_PER_VIEW:
            raise DashboardValidationError(
                f"view already has the maximum of {MAX_CARDS_PER_VIEW} cards"
            )
        normalized = normalize_card_helper(card)
        self._insert_item(view["cards"], normalized, position)
        document["dashboard_version"] += 1
        self._write_document(document)
        return clone_card(normalized), document["dashboard_version"]

    def update_card(
        self,
        dashboard_id: str,
        view_id: str,
        card_id: str,
        card: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        view = self._find_view(document, validate_view_id(view_id))
        card_id = validate_card_id(card_id)
        for index, existing in enumerate(view["cards"]):
            if existing["card_id"] == card_id:
                normalized = normalize_card_helper(card, card_id=card_id)
                view["cards"][index] = normalized
                document["dashboard_version"] += 1
                self._write_document(document)
                return clone_card(normalized), document["dashboard_version"]
        raise DashboardNotFoundError(f"card not found: {card_id}")

    def delete_card(
        self,
        dashboard_id: str,
        view_id: str,
        card_id: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        view = self._find_view(document, validate_view_id(view_id))
        card_id = validate_card_id(card_id)
        for index, existing in enumerate(view["cards"]):
            if existing["card_id"] == card_id:
                view["cards"].pop(index)
                document["dashboard_version"] += 1
                self._write_document(document)
                return {
                    "dashboard_id": dashboard_id,
                    "view_id": view_id,
                    "card_id": card_id,
                    "deleted": True,
                    "dashboard_version": document["dashboard_version"],
                }
        raise DashboardNotFoundError(f"card not found: {card_id}")

    def patch_dashboard(
        self,
        dashboard_id: str,
        operations: list[dict[str, Any]],
        *,
        expected_version: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        ensure_expected_version(document, expected_version)
        patched, applied = apply_json_patch(document, operations)
        validated = self._normalize_existing_document(patched)
        validated["dashboard_version"] = document["dashboard_version"] + 1
        self._write_document(validated)
        return deepcopy(validated), applied

    def validate_dashboard(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        return self._normalize_existing_document(deepcopy(dashboard))

    def validate_patch(
        self, dashboard_id: str, operations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        document = self._read_document(validate_dashboard_id(dashboard_id))
        patched, _ = apply_json_patch(document, operations)
        return self._normalize_existing_document(patched)

    def _normalize_existing_document(self, document: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise DashboardValidationError("dashboard document must be an object")
        metadata = normalize_dashboard_metadata(document["metadata"])
        views = [self._normalize_view(view) for view in document.get("views", [])]
        self._ensure_view_uniqueness(views)
        version = ensure_integer(document.get("dashboard_version", 0), "dashboard_version")
        return {"metadata": metadata, "views": views, "dashboard_version": version}

    def _normalize_view(self, view: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(view, dict):
            raise DashboardValidationError("view must be an object")
        reject_unknown_keys(view, {"view_id", "title", "path", "icon", "cards"}, "view")
        normalized = {
            "view_id": validate_view_id(view["view_id"]),
            "title": validate_title(view["title"]),
            "path": validate_url_path(view["path"]),
            "cards": [normalize_card_helper(card) for card in view.get("cards", [])],
        }
        if "icon" in view and view["icon"] is not None:
            from .validation import validate_icon

            normalized["icon"] = validate_icon(view["icon"])
        return normalized

    def _ensure_view_uniqueness(self, views: list[dict[str, Any]]) -> None:
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        for view in views:
            if view["view_id"] in seen_ids:
                raise DashboardConflictError(f"duplicate view_id: {view['view_id']}")
            if view["path"] in seen_paths:
                raise DashboardConflictError(f"duplicate view path: {view['path']}")
            seen_ids.add(view["view_id"])
            seen_paths.add(view["path"])

    def _document_path(self, dashboard_id: str) -> Path:
        return self._managed_path / f"{dashboard_id}.json"

    def _render_path(self, dashboard_id: str) -> Path:
        return self._rendered_path / f"{dashboard_id}.yaml"

    def _read_document(self, dashboard_id: str) -> dict[str, Any]:
        path = self._document_path(dashboard_id)
        if not path.exists():
            raise DashboardNotFoundError(f"dashboard not found: {dashboard_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_document(self, document: dict[str, Any]) -> None:
        dashboard_id = document["metadata"]["dashboard_id"]
        self._write_text_atomically(
            self._document_path(dashboard_id),
            json.dumps(document, indent=2, sort_keys=True) + "\n",
        )
        self._write_text_atomically(
            self._render_path(dashboard_id),
            dump_yaml(self._render_dashboard(document)),
        )

    def _write_text_atomically(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                prefix=f".{path.name}.",
                suffix=".tmp",
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)
            temp_path.replace(path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _render_dashboard(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": document["metadata"]["title"],
            "views": [self._render_view(view) for view in document["views"]],
        }

    def _render_view(self, view: dict[str, Any]) -> dict[str, Any]:
        rendered = {
            "title": view["title"],
            "path": view["path"],
            "cards": [render_card_config(card) for card in view["cards"]],
        }
        if "icon" in view:
            rendered["icon"] = view["icon"]
        return rendered

    def _view_summary(self, view: dict[str, Any]) -> dict[str, Any]:
        summary = {
            "view_id": view["view_id"],
            "title": view["title"],
            "path": view["path"],
            "card_count": len(view["cards"]),
        }
        if "icon" in view:
            summary["icon"] = view["icon"]
        return summary

    def _find_view(self, document: dict[str, Any], view_id: str) -> dict[str, Any]:
        for view in document["views"]:
            if view["view_id"] == view_id:
                return view
        raise DashboardNotFoundError(f"view not found: {view_id}")

    def _find_view_index(self, document: dict[str, Any], view_id: str) -> int:
        for index, view in enumerate(document["views"]):
            if view["view_id"] == view_id:
                return index
        raise DashboardNotFoundError(f"view not found: {view_id}")

    def _insert_item(self, items: list[dict[str, Any]], item: dict[str, Any], position: int | None) -> None:
        if position is None:
            items.append(item)
            return
        position = ensure_integer(position, "position")
        if position > len(items):
            raise DashboardValidationError("position is out of range")
        items.insert(position, item)
