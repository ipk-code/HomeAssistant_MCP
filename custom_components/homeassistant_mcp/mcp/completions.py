"""Completion registry helpers for MCP capabilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

from ..discovery import HomeAssistantDiscoveryProvider
from ..lovelace.errors import DashboardNotFoundError
from ..lovelace.repository import YamlDashboardRepository

CompletionProvider = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
MAX_COMPLETION_VALUES = 25

_COMMON_ICONS = (
    "mdi:home",
    "mdi:lightbulb",
    "mdi:thermometer",
    "mdi:flash",
    "mdi:gauge",
    "mdi:water",
    "mdi:weather-sunny",
    "mdi:shield-home",
    "mdi:camera",
    "mdi:motion-sensor",
    "mdi:power-plug",
    "mdi:fan",
    "mdi:robot-vacuum",
    "mdi:door",
    "mdi:window-open",
    "mdi:chart-line",
    "mdi:calendar",
    "mdi:cog",
    "mdi:sofa",
    "mdi:bed-king-outline",
)


class CompletionRegistry:
    """Registry for MCP completion providers."""

    def __init__(self) -> None:
        self._providers: dict[tuple[str | None, str], CompletionProvider] = {}

    def register(
        self,
        *,
        argument_name: str,
        provider: CompletionProvider,
        ref_name: str | None = None,
    ) -> None:
        """Register a completion provider for a ref and argument pair."""
        self._providers[(ref_name, argument_name)] = provider

    def complete(self, ref: dict[str, Any], argument: dict[str, Any]) -> dict[str, Any]:
        """Return completion candidates for one argument."""
        argument_name = argument.get("name")
        if not isinstance(argument_name, str):
            return {"values": [], "hasMore": False}

        ref_name = ref.get("name") if isinstance(ref.get("name"), str) else None
        provider = self._providers.get((ref_name, argument_name))
        if provider is None:
            provider = self._providers.get((None, argument_name))
        if provider is None:
            return {"values": [], "hasMore": False}
        return _normalize_completion_result(provider(ref, argument))

    def provider_count(self) -> int:
        """Return the number of registered completion providers."""
        return len(self._providers)


def register_builtin_completions(
    registry: CompletionRegistry,
    *,
    repository: YamlDashboardRepository,
    discovery: HomeAssistantDiscoveryProvider,
) -> None:
    """Register the built-in completion providers for shipped identifiers."""
    registry.register(
        argument_name="entity_id",
        provider=lambda ref, argument: _complete_values(
            discovery.list_entity_ids(),
            _prefix(argument),
        ),
    )
    registry.register(
        argument_name="dashboard_id",
        provider=lambda ref, argument: _complete_values(
            [dashboard["dashboard_id"] for dashboard in repository.list_dashboards()],
            _prefix(argument),
        ),
    )
    registry.register(
        argument_name="view_id",
        provider=lambda ref, argument: _complete_view_ids(
            repository,
            ref,
            _prefix(argument),
        ),
    )
    registry.register(
        argument_name="card_id",
        provider=lambda ref, argument: _complete_card_ids(
            repository,
            ref,
            _prefix(argument),
        ),
    )
    registry.register(
        argument_name="icon",
        provider=lambda ref, argument: _complete_values(
            _COMMON_ICONS,
            _prefix(argument),
        ),
    )


def _complete_view_ids(
    repository: YamlDashboardRepository,
    ref: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    dashboard_id = _context_arguments(ref).get("dashboard_id")
    if not isinstance(dashboard_id, str):
        return {"values": [], "hasMore": False}
    try:
        views = repository.list_views(dashboard_id)
    except DashboardNotFoundError:
        return {"values": [], "hasMore": False}
    return _complete_values([view["view_id"] for view in views], prefix)


def _complete_card_ids(
    repository: YamlDashboardRepository,
    ref: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    context = _context_arguments(ref)
    dashboard_id = context.get("dashboard_id")
    view_id = context.get("view_id")
    if not isinstance(dashboard_id, str) or not isinstance(view_id, str):
        return {"values": [], "hasMore": False}
    try:
        cards = repository.list_cards(dashboard_id, view_id)
    except DashboardNotFoundError:
        return {"values": [], "hasMore": False}
    return _complete_values(
        [card["card_id"] for card in cards if isinstance(card.get("card_id"), str)],
        prefix,
    )


def _context_arguments(ref: dict[str, Any]) -> dict[str, Any]:
    arguments = ref.get("arguments")
    if isinstance(arguments, dict):
        return arguments
    return {}


def _prefix(argument: dict[str, Any]) -> str:
    value = argument.get("value")
    return value if isinstance(value, str) else ""


def _complete_values(values: Iterable[str], prefix: str) -> dict[str, Any]:
    lowered_prefix = prefix.casefold()
    matches = []
    seen = set()
    for value in sorted(values, key=str.casefold):
        if value in seen:
            continue
        if lowered_prefix and not value.casefold().startswith(lowered_prefix):
            continue
        seen.add(value)
        matches.append(value)
    return {
        "values": matches[:MAX_COMPLETION_VALUES],
        "hasMore": len(matches) > MAX_COMPLETION_VALUES,
    }


def _normalize_completion_result(result: dict[str, Any]) -> dict[str, Any]:
    values = result.get("values", []) if isinstance(result, dict) else []
    normalized = []
    seen = set()
    if isinstance(values, list):
        for value in values:
            if not isinstance(value, str) or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
    has_more = bool(result.get("hasMore")) if isinstance(result, dict) else False
    if len(normalized) > MAX_COMPLETION_VALUES:
        has_more = True
    return {
        "values": normalized[:MAX_COMPLETION_VALUES],
        "hasMore": has_more,
    }
