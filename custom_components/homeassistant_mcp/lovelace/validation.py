"""Validation helpers for canonical Lovelace dashboard documents."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .errors import DashboardConflictError, DashboardValidationError

_DASHBOARD_ID_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,63}$")
_VIEW_ID_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,63}$")
_CARD_ID_RE = re.compile(r"^[A-Za-z0-9_:-]{1,64}$")
_URL_PATH_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_ICON_RE = re.compile(r"^[A-Za-z0-9:_-]{1,64}$")
_ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
# CWE-601: The local-path branch must reject protocol-relative URLs
# (//evil.com) that browsers resolve to the current page's protocol,
# enabling open-redirect attacks.  Require "/" followed by a non-"/"
# character (or end-of-string for the bare "/" root path).
_SAFE_URL_RE = re.compile(r"^(https?://[^\s]+|/([^\s/][^\s]*)?)$")


def _require_string(value: Any, field: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise DashboardValidationError(f"{field} must be a string")
    if not value or len(value) > max_length:
        raise DashboardValidationError(
            f"{field} must be between 1 and {max_length} characters"
        )
    return value


def reject_unknown_keys(payload: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = set(payload) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise DashboardValidationError(f"{field} contains unsupported fields: {names}")


def validate_identifier(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    text = _require_string(value, field, max_length=64)
    if not pattern.fullmatch(text):
        raise DashboardValidationError(f"{field} has an invalid format")
    return text


def validate_dashboard_id(value: Any) -> str:
    return validate_identifier(value, "dashboard_id", _DASHBOARD_ID_RE)


def validate_view_id(value: Any) -> str:
    return validate_identifier(value, "view_id", _VIEW_ID_RE)


def validate_card_id(value: Any) -> str:
    return validate_identifier(value, "card_id", _CARD_ID_RE)


def validate_url_path(value: Any) -> str:
    text = validate_identifier(value, "url_path", _URL_PATH_RE)
    if text in {"api", "config", "static"}:
        raise DashboardValidationError("url_path uses a reserved route")
    return text


def validate_title(value: Any, field: str = "title") -> str:
    return _require_string(value, field, max_length=128)


def validate_markdown_content(value: Any) -> str:
    return _require_string(value, "content", max_length=20000)


def validate_icon(value: Any) -> str:
    text = _require_string(value, "icon", max_length=64)
    if not _ICON_RE.fullmatch(text):
        raise DashboardValidationError("icon has an invalid format")
    return text


def validate_entity_id(value: Any) -> str:
    text = _require_string(value, "entity_id", max_length=128)
    if not _ENTITY_ID_RE.fullmatch(text):
        raise DashboardValidationError("entity_id has an invalid format")
    return text


def validate_safe_url(value: Any) -> str:
    text = _require_string(value, "url", max_length=2048)
    if not _SAFE_URL_RE.fullmatch(text):
        raise DashboardValidationError("url must be http(s) or start with '/'")
    return text


def validate_navigation_path(value: Any) -> str:
    text = _require_string(value, "navigation_path", max_length=256)
    if not text.startswith("/") or any(ch.isspace() for ch in text):
        raise DashboardValidationError("navigation_path must be an internal path")
    return text


def ensure_boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise DashboardValidationError(f"{field} must be a boolean")
    return value


def ensure_number(value: Any, field: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DashboardValidationError(f"{field} must be numeric")
    # CWE-20: Reject special float values that produce non-standard JSON
    # tokens (NaN, Infinity, -Infinity) which corrupt persisted documents
    # and break cross-system interoperability.
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        raise DashboardValidationError(f"{field} must be a finite number")
    return value


def ensure_integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DashboardValidationError(f"{field} must be an integer")
    if value < minimum:
        raise DashboardValidationError(f"{field} must be >= {minimum}")
    return value


def ensure_expected_version(document: dict[str, Any], expected_version: int | None) -> None:
    if expected_version is None:
        return
    version = ensure_integer(expected_version, "expected_version", minimum=0)
    if version != document["dashboard_version"]:
        raise DashboardConflictError(
            f"expected_version {version} does not match dashboard_version {document['dashboard_version']}"
        )


def normalize_dashboard_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    reject_unknown_keys(
        metadata,
        {"dashboard_id", "title", "url_path", "icon", "show_in_sidebar", "require_admin", "mode"},
        "dashboard metadata",
    )
    normalized = {
        "dashboard_id": validate_dashboard_id(metadata["dashboard_id"]),
        "title": validate_title(metadata["title"]),
        "url_path": validate_url_path(metadata["url_path"]),
        "mode": "yaml",
        "show_in_sidebar": ensure_boolean(
            metadata.get("show_in_sidebar", True), "show_in_sidebar"
        ),
        "require_admin": ensure_boolean(
            metadata.get("require_admin", False), "require_admin"
        ),
    }
    if "mode" in metadata and metadata["mode"] != "yaml":
        raise DashboardValidationError("mode must be 'yaml'")
    if "icon" in metadata and metadata["icon"] is not None:
        normalized["icon"] = validate_icon(metadata["icon"])
    return normalized


def apply_metadata_patch(metadata: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if not patch:
        raise DashboardValidationError("metadata patch must not be empty")
    reject_unknown_keys(
        patch, {"title", "icon", "show_in_sidebar", "require_admin"}, "metadata patch"
    )
    updated = deepcopy(metadata)
    for key, value in patch.items():
        if key not in {"title", "icon", "show_in_sidebar", "require_admin"}:
            raise DashboardValidationError(f"unsupported metadata field: {key}")
        if key == "title":
            updated[key] = validate_title(value)
        elif key == "icon":
            updated[key] = validate_icon(value)
        else:
            updated[key] = ensure_boolean(value, key)
    return updated
