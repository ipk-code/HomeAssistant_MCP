"""Typed card helper normalization and rendering."""

from __future__ import annotations

from copy import deepcopy
from itertools import count
from typing import Any

from .errors import DashboardValidationError
from .validation import (
    ensure_boolean,
    ensure_number,
    reject_unknown_keys,
    validate_card_id,
    validate_entity_id,
    validate_icon,
    validate_markdown_content,
    validate_navigation_path,
    validate_safe_url,
    validate_title,
)

_CARD_SEQUENCE = count(1)
_SIMPLE_KINDS = {"heading", "markdown", "gauge", "tile", "entities", "glance"}
_NESTED_KINDS = {"grid", "horizontal_stack", "vertical_stack"}
_SUPPORTED_KINDS = _SIMPLE_KINDS | _NESTED_KINDS


def _next_card_id() -> str:
    return f"card:{next(_CARD_SEQUENCE)}"


def _normalize_tap_action(tap_action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(tap_action, dict):
        raise DashboardValidationError("tap_action must be an object")
    reject_unknown_keys(tap_action, {"action", "navigation_path", "url"}, "tap_action")
    action = tap_action.get("action")
    if action not in {"more-info", "toggle", "navigate", "url", "none"}:
        raise DashboardValidationError("tap_action.action is invalid")
    normalized = {"action": action}
    if "navigation_path" in tap_action:
        normalized["navigation_path"] = validate_navigation_path(
            tap_action["navigation_path"]
        )
    if "url" in tap_action:
        normalized["url"] = validate_safe_url(tap_action["url"])
    if action == "navigate" and "navigation_path" not in normalized:
        raise DashboardValidationError("navigate action requires navigation_path")
    if action == "url" and "url" not in normalized:
        raise DashboardValidationError("url action requires url")
    return normalized


def _normalize_entity_row(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise DashboardValidationError("entity rows must be objects")
    reject_unknown_keys(row, {"entity_id", "name", "icon"}, "entity row")
    normalized = {"entity_id": validate_entity_id(row["entity_id"])}
    if "name" in row:
        normalized["name"] = validate_title(row["name"], field="name")
    if "icon" in row:
        normalized["icon"] = validate_icon(row["icon"])
    return normalized


def normalize_card_helper(card: dict[str, Any], *, card_id: str | None = None) -> dict[str, Any]:
    """Normalize a typed card helper input into canonical form."""
    if not isinstance(card, dict):
        raise DashboardValidationError("card must be an object")
    kind = card.get("kind")
    if kind not in _SUPPORTED_KINDS:
        raise DashboardValidationError(f"unsupported card kind: {kind}")

    normalized: dict[str, Any] = {
        "kind": kind,
        "card_id": validate_card_id(card_id or card.get("card_id") or _next_card_id()),
    }

    if kind == "heading":
        reject_unknown_keys(card, {"kind", "card_id", "title", "icon"}, "heading card")
        normalized["title"] = validate_title(card["title"])
        if "icon" in card:
            normalized["icon"] = validate_icon(card["icon"])
        return normalized

    if kind == "markdown":
        reject_unknown_keys(
            card, {"kind", "card_id", "title", "content", "text_only"}, "markdown card"
        )
        normalized["content"] = validate_markdown_content(card["content"])
        if "title" in card:
            normalized["title"] = validate_title(card["title"])
        if "text_only" in card:
            normalized["text_only"] = ensure_boolean(card["text_only"], "text_only")
        return normalized

    if kind == "gauge":
        reject_unknown_keys(card, {"kind", "card_id", "entity_id", "title", "min", "max"}, "gauge card")
        normalized["entity_id"] = validate_entity_id(card["entity_id"])
        if "title" in card:
            normalized["title"] = validate_title(card["title"])
        if "min" in card:
            normalized["min"] = ensure_number(card["min"], "min")
        if "max" in card:
            normalized["max"] = ensure_number(card["max"], "max")
        return normalized

    if kind == "tile":
        reject_unknown_keys(card, {"kind", "card_id", "entity_id", "title", "icon", "tap_action"}, "tile card")
        normalized["entity_id"] = validate_entity_id(card["entity_id"])
        if "title" in card:
            normalized["title"] = validate_title(card["title"])
        if "icon" in card:
            normalized["icon"] = validate_icon(card["icon"])
        if "tap_action" in card:
            normalized["tap_action"] = _normalize_tap_action(card["tap_action"])
        return normalized

    if kind == "entities":
        reject_unknown_keys(
            card,
            {"kind", "card_id", "title", "show_header_toggle", "entities"},
            "entities card",
        )
        entities = card.get("entities")
        if not isinstance(entities, list) or not entities:
            raise DashboardValidationError("entities cards require at least one entity")
        normalized["entities"] = [_normalize_entity_row(row) for row in entities]
        if "title" in card:
            normalized["title"] = validate_title(card["title"])
        if "show_header_toggle" in card:
            normalized["show_header_toggle"] = ensure_boolean(
                card["show_header_toggle"], "show_header_toggle"
            )
        return normalized

    if kind == "glance":
        reject_unknown_keys(
            card,
            {"kind", "card_id", "title", "show_name", "show_icon", "show_state", "entities"},
            "glance card",
        )
        entities = card.get("entities")
        if not isinstance(entities, list) or not entities:
            raise DashboardValidationError("glance cards require at least one entity")
        normalized["entities"] = [_normalize_entity_row(row) for row in entities]
        if "title" in card:
            normalized["title"] = validate_title(card["title"])
        for field in ("show_name", "show_icon", "show_state"):
            if field in card:
                normalized[field] = ensure_boolean(card[field], field)
        return normalized

    reject_unknown_keys(
        card,
        {"kind", "card_id", "title", "columns", "square", "cards"}
        if kind == "grid"
        else {"kind", "card_id", "cards"},
        f"{kind} card",
    )
    cards = card.get("cards")
    if not isinstance(cards, list) or not cards:
        raise DashboardValidationError(f"{kind} cards require nested cards")
    normalized["cards"] = [normalize_card_helper(item) for item in cards]
    if kind == "grid":
        columns = card.get("columns")
        if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= 6:
            raise DashboardValidationError("grid columns must be an integer between 1 and 6")
        normalized["columns"] = columns
        if "title" in card:
            normalized["title"] = validate_title(card["title"])
        if "square" in card:
            normalized["square"] = ensure_boolean(card["square"], "square")
    return normalized


def render_card_config(card: dict[str, Any]) -> dict[str, Any]:
    """Convert a canonical card helper into raw Lovelace card config."""
    kind = card["kind"]
    raw: dict[str, Any] = {}
    if kind == "heading":
        raw = {"type": "heading", "heading": card["title"]}
        if "icon" in card:
            raw["icon"] = card["icon"]
        return raw
    if kind == "markdown":
        raw = {"type": "markdown", "content": card["content"]}
        if "title" in card:
            raw["title"] = card["title"]
        if "text_only" in card:
            raw["text_only"] = card["text_only"]
        return raw
    if kind == "gauge":
        raw = {"type": "gauge", "entity": card["entity_id"]}
        if "title" in card:
            raw["name"] = card["title"]
        if "min" in card:
            raw["min"] = card["min"]
        if "max" in card:
            raw["max"] = card["max"]
        return raw
    if kind == "tile":
        raw = {"type": "tile", "entity": card["entity_id"]}
        if "title" in card:
            raw["name"] = card["title"]
        if "icon" in card:
            raw["icon"] = card["icon"]
        if "tap_action" in card:
            raw["tap_action"] = deepcopy(card["tap_action"])
        return raw
    if kind == "entities":
        raw = {
            "type": "entities",
            "entities": [_render_entity_row(row) for row in card["entities"]],
        }
        if "title" in card:
            raw["title"] = card["title"]
        if "show_header_toggle" in card:
            raw["show_header_toggle"] = card["show_header_toggle"]
        return raw
    if kind == "glance":
        raw = {
            "type": "glance",
            "entities": [_render_entity_row(row) for row in card["entities"]],
        }
        if "title" in card:
            raw["title"] = card["title"]
        for field in ("show_name", "show_icon", "show_state"):
            if field in card:
                raw[field] = card[field]
        return raw
    if kind == "grid":
        raw = {
            "type": "grid",
            "columns": card["columns"],
            "cards": [render_card_config(item) for item in card["cards"]],
        }
        if "title" in card:
            raw["title"] = card["title"]
        if "square" in card:
            raw["square"] = card["square"]
        return raw
    if kind == "horizontal_stack":
        return {
            "type": "horizontal-stack",
            "cards": [render_card_config(item) for item in card["cards"]],
        }
    if kind == "vertical_stack":
        return {
            "type": "vertical-stack",
            "cards": [render_card_config(item) for item in card["cards"]],
        }
    raise DashboardValidationError(f"unsupported card kind: {kind}")


def _render_entity_row(row: dict[str, Any]) -> str | dict[str, Any]:
    raw = {"entity": row["entity_id"]}
    if "name" in row:
        raw["name"] = row["name"]
    if "icon" in row:
        raw["icon"] = row["icon"]
    if set(raw) == {"entity"}:
        return row["entity_id"]
    return raw


def clone_card(card: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(card)
