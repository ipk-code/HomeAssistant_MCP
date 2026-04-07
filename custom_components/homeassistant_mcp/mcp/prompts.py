"""Prompt registry helpers for MCP capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import json
from typing import Any, Awaitable, Callable

from ..discovery import HomeAssistantDiscoveryProvider
from ..managed import ManagedDashboardExecutor
from ..lovelace.errors import DashboardNotFoundError
from ..lovelace.repository import YamlDashboardRepository

PromptHandler = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]

_SUPPORTED_CARD_KINDS = (
    "heading",
    "markdown",
    "gauge",
    "tile",
    "entities",
    "glance",
    "grid",
    "horizontal_stack",
    "vertical_stack",
)
_MAX_PROMPT_SUMMARY_ITEMS = 25


@dataclass(frozen=True)
class PromptArgument:
    """Serializable MCP prompt argument definition."""

    name: str
    description: str
    required: bool = False

    def as_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }


@dataclass(frozen=True)
class PromptDefinition:
    """Serializable MCP prompt definition."""

    name: str
    description: str
    arguments: tuple[PromptArgument, ...] = field(default_factory=tuple)

    def as_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [argument.as_mcp() for argument in self.arguments],
        }


class PromptRegistry:
    """Registry for MCP prompt definitions and handlers."""

    def __init__(self) -> None:
        self._prompts: dict[str, tuple[PromptDefinition, PromptHandler]] = {}

    def register(self, definition: PromptDefinition, handler: PromptHandler) -> None:
        """Register a prompt definition and handler."""
        self._prompts[definition.name] = (definition, handler)

    def list_prompts(self) -> list[dict[str, Any]]:
        """Return serialized MCP prompt definitions."""
        return [definition.as_mcp() for definition, _handler in self._prompts.values()]

    def get(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return one prompt payload by name."""
        try:
            _definition, handler = self._prompts[name]
        except KeyError as err:
            raise KeyError(f"unknown prompt: {name}") from err
        result = handler(arguments)
        if inspect.isawaitable(result):
            raise RuntimeError("async prompt handler requires async_get")
        return result

    async def async_get(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return one prompt payload by name, awaiting async handlers when needed."""
        try:
            _definition, handler = self._prompts[name]
        except KeyError as err:
            raise KeyError(f"unknown prompt: {name}") from err
        result = handler(arguments)
        if inspect.isawaitable(result):
            result = await result
        return result


def register_builtin_prompts(
    registry: PromptRegistry,
    *,
    repository: YamlDashboardRepository,
    discovery: HomeAssistantDiscoveryProvider,
    managed: ManagedDashboardExecutor | None = None,
) -> None:
    """Register the shipped dashboard-focused prompt catalog."""
    registry.register(
        PromptDefinition(
            name="dashboard.builder",
            description="Plan or extend a Lovelace dashboard using discovery context and typed MCP tools.",
            arguments=(
                PromptArgument(
                    "dashboard_id", "Target dashboard identifier if updating."
                ),
                PromptArgument(
                    "area_id", "Preferred Home Assistant area for the dashboard."
                ),
                PromptArgument(
                    "goal",
                    "Short description of what the dashboard should optimize for.",
                ),
            ),
        ),
        (
            (
                lambda arguments: _dashboard_builder_prompt_async(
                    managed, discovery, arguments
                )
            )
            if managed is not None
            else lambda arguments: _dashboard_builder_prompt(
                repository, discovery, arguments
            )
        ),
    )
    registry.register(
        PromptDefinition(
            name="dashboard.review",
            description="Review one managed dashboard for structure, clarity, and next MCP changes.",
            arguments=(
                PromptArgument(
                    "dashboard_id",
                    "Managed dashboard identifier to review.",
                    required=True,
                ),
            ),
        ),
        (
            (lambda arguments: _dashboard_review_prompt_async(managed, arguments))
            if managed is not None
            else lambda arguments: _dashboard_review_prompt(repository, arguments)
        ),
    )
    registry.register(
        PromptDefinition(
            name="dashboard.layout_consistency_review",
            description="Check a dashboard for view naming, card grouping, and layout consistency.",
            arguments=(
                PromptArgument(
                    "dashboard_id",
                    "Managed dashboard identifier to inspect.",
                    required=True,
                ),
            ),
        ),
        (
            (lambda arguments: _layout_consistency_prompt_async(managed, arguments))
            if managed is not None
            else lambda arguments: _layout_consistency_prompt(repository, arguments)
        ),
    )
    registry.register(
        PromptDefinition(
            name="dashboard.entity_card_mapping",
            description="Suggest supported typed card helpers for one Home Assistant entity.",
            arguments=(
                PromptArgument(
                    "entity_id",
                    "Home Assistant entity identifier to map.",
                    required=True,
                ),
                PromptArgument(
                    "dashboard_id",
                    "Managed dashboard identifier for placement context.",
                ),
                PromptArgument(
                    "view_id", "Managed view identifier for placement context."
                ),
            ),
        ),
        (
            (
                lambda arguments: _entity_card_mapping_prompt_async(
                    managed, discovery, arguments
                )
            )
            if managed is not None
            else lambda arguments: _entity_card_mapping_prompt(
                repository, discovery, arguments
            )
        ),
    )
    registry.register(
        PromptDefinition(
            name="dashboard.cleanup_audit",
            description="Audit a dashboard for cleanup opportunities and low-risk follow-up edits.",
            arguments=(
                PromptArgument(
                    "dashboard_id",
                    "Managed dashboard identifier to audit.",
                    required=True,
                ),
            ),
        ),
        (
            (lambda arguments: _dashboard_cleanup_prompt_async(managed, arguments))
            if managed is not None
            else lambda arguments: _dashboard_cleanup_prompt(repository, arguments)
        ),
    )


async def _dashboard_builder_prompt_async(
    managed: ManagedDashboardExecutor,
    discovery: HomeAssistantDiscoveryProvider,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = arguments.get("dashboard_id")
    area_id = arguments.get("area_id")
    goal = arguments.get("goal")
    dashboards = _bounded_items(await managed.list_dashboards())
    area_summary = (
        _lookup_area(discovery, area_id) if isinstance(area_id, str) else None
    )

    lines = [
        "Design or extend a Lovelace dashboard using `homeassistant_mcp`.",
        f"Available managed dashboards: {json.dumps(dashboards, indent=2)}",
        f"Supported typed card kinds: {', '.join(_SUPPORTED_CARD_KINDS)}.",
        "Recommended workflow:",
        "1. Read `hass://areas`, `hass://entities`, and `hass://services` for context.",
        "2. If you are updating a dashboard, read `hass://dashboard/{dashboard_id}` before proposing changes.",
        "3. Use `completion/complete` for `entity_id`, `icon`, `view_id`, and `card_id` whenever identifiers are uncertain.",
        "4. Prefer typed `lovelace.*` tools over free-form patches unless a targeted patch is clearly smaller.",
    ]
    if isinstance(goal, str) and goal:
        lines.insert(1, f"Goal: {goal}")
    if isinstance(dashboard_id, str) and dashboard_id:
        lines.insert(1, f"Target dashboard_id: {dashboard_id}")
    if area_summary is not None:
        lines.insert(
            1, f"Preferred area context: {json.dumps(area_summary, sort_keys=True)}"
        )
    return _prompt_result("Dashboard builder", lines)


async def _dashboard_review_prompt_async(
    managed: ManagedDashboardExecutor,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = _require_string(arguments, "dashboard_id")
    summary = await _dashboard_summary_async(managed, dashboard_id)
    lines = [
        f"Review managed dashboard `{dashboard_id}` for clarity, navigation, grouping, and follow-up MCP changes.",
        f"Dashboard summary: {json.dumps(summary, indent=2)}",
        f"Read `hass://dashboard/{dashboard_id}` before suggesting edits.",
        "Focus on title clarity, view purpose, card density, icon consistency, and whether the current views match the available entities.",
        "Return concrete recommendations and the smallest typed `lovelace.*` operations needed to apply them.",
    ]
    return _prompt_result(f"Dashboard review for {dashboard_id}", lines)


async def _layout_consistency_prompt_async(
    managed: ManagedDashboardExecutor,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = _require_string(arguments, "dashboard_id")
    summary = await _dashboard_summary_async(managed, dashboard_id)
    lines = [
        f"Review dashboard `{dashboard_id}` for layout consistency.",
        f"Dashboard summary: {json.dumps(summary, indent=2)}",
        "Check for inconsistent view titles, paths, icons, card grouping, and repeated card patterns that should be normalized.",
        f"Use `hass://dashboard/{dashboard_id}` to inspect the full document and propose minimal typed `lovelace.*` changes.",
    ]
    return _prompt_result(f"Layout consistency review for {dashboard_id}", lines)


async def _entity_card_mapping_prompt_async(
    managed: ManagedDashboardExecutor,
    discovery: HomeAssistantDiscoveryProvider,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    entity_id = _require_string(arguments, "entity_id")
    entity_summary = discovery.get_entity_summary(entity_id)
    dashboard_id = arguments.get("dashboard_id")
    view_id = arguments.get("view_id")
    suggestions = _recommended_card_kinds(entity_summary)

    lines = [
        f"Suggest the best supported typed helper cards for entity `{entity_id}`.",
        f"Entity summary: {json.dumps(entity_summary, indent=2)}",
        f"Recommended card kinds in this server: {', '.join(suggestions)}.",
        "Explain which card kind is the best primary choice and which alternative layouts are acceptable.",
        "Include the exact `lovelace.create_card` or `lovelace.update_card` payload you would use.",
    ]
    if isinstance(dashboard_id, str) and dashboard_id:
        lines.append(f"Placement dashboard_id: `{dashboard_id}`.")
    if isinstance(view_id, str) and view_id:
        lines.append(f"Placement view_id: `{view_id}`.")
    if isinstance(dashboard_id, str) and dashboard_id:
        try:
            summary = await _dashboard_summary_async(managed, dashboard_id)
        except KeyError:
            lines.append(
                f"Dashboard `{dashboard_id}` is not currently managed; treat this as a new placement target."
            )
        else:
            lines.append(
                f"Placement dashboard summary: {json.dumps(summary, indent=2)}"
            )
    return _prompt_result(f"Entity card mapping for {entity_id}", lines)


async def _dashboard_cleanup_prompt_async(
    managed: ManagedDashboardExecutor,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = _require_string(arguments, "dashboard_id")
    summary = await _dashboard_summary_async(managed, dashboard_id)
    lines = [
        f"Audit dashboard `{dashboard_id}` for cleanup opportunities.",
        f"Dashboard summary: {json.dumps(summary, indent=2)}",
        f"Read `hass://dashboard/{dashboard_id}` and look for redundant views, vague titles, over-nested stacks, and cards that should be consolidated.",
        "Prefer low-risk cleanups that can be expressed as a short sequence of typed `lovelace.*` calls.",
    ]
    return _prompt_result(f"Cleanup audit for {dashboard_id}", lines)


def _dashboard_builder_prompt(
    repository: YamlDashboardRepository,
    discovery: HomeAssistantDiscoveryProvider,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = arguments.get("dashboard_id")
    area_id = arguments.get("area_id")
    goal = arguments.get("goal")
    dashboards = _bounded_items(repository.list_dashboards())
    area_summary = (
        _lookup_area(discovery, area_id) if isinstance(area_id, str) else None
    )

    lines = [
        "Design or extend a Lovelace dashboard using `homeassistant_mcp`.",
        f"Available managed dashboards: {json.dumps(dashboards, indent=2)}",
        f"Supported typed card kinds: {', '.join(_SUPPORTED_CARD_KINDS)}.",
        "Recommended workflow:",
        "1. Read `hass://areas`, `hass://entities`, and `hass://services` for context.",
        "2. If you are updating a dashboard, read `hass://dashboard/{dashboard_id}` before proposing changes.",
        "3. Use `completion/complete` for `entity_id`, `icon`, `view_id`, and `card_id` whenever identifiers are uncertain.",
        "4. Prefer typed `lovelace.*` tools over free-form patches unless a targeted patch is clearly smaller.",
    ]
    if isinstance(goal, str) and goal:
        lines.insert(1, f"Goal: {goal}")
    if isinstance(dashboard_id, str) and dashboard_id:
        lines.insert(1, f"Target dashboard_id: {dashboard_id}")
    if area_summary is not None:
        lines.insert(
            1, f"Preferred area context: {json.dumps(area_summary, sort_keys=True)}"
        )
    return _prompt_result("Dashboard builder", lines)


def _dashboard_review_prompt(
    repository: YamlDashboardRepository,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = _require_string(arguments, "dashboard_id")
    summary = _dashboard_summary(repository, dashboard_id)
    lines = [
        f"Review managed dashboard `{dashboard_id}` for clarity, navigation, grouping, and follow-up MCP changes.",
        f"Dashboard summary: {json.dumps(summary, indent=2)}",
        f"Read `hass://dashboard/{dashboard_id}` before suggesting edits.",
        "Focus on title clarity, view purpose, card density, icon consistency, and whether the current views match the available entities.",
        "Return concrete recommendations and the smallest typed `lovelace.*` operations needed to apply them.",
    ]
    return _prompt_result(f"Dashboard review for {dashboard_id}", lines)


def _layout_consistency_prompt(
    repository: YamlDashboardRepository,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = _require_string(arguments, "dashboard_id")
    summary = _dashboard_summary(repository, dashboard_id)
    lines = [
        f"Review dashboard `{dashboard_id}` for layout consistency.",
        f"Dashboard summary: {json.dumps(summary, indent=2)}",
        "Check for inconsistent view titles, paths, icons, card grouping, and repeated card patterns that should be normalized.",
        f"Use `hass://dashboard/{dashboard_id}` to inspect the full document and propose minimal typed `lovelace.*` changes.",
    ]
    return _prompt_result(f"Layout consistency review for {dashboard_id}", lines)


def _entity_card_mapping_prompt(
    repository: YamlDashboardRepository,
    discovery: HomeAssistantDiscoveryProvider,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    entity_id = _require_string(arguments, "entity_id")
    entity_summary = discovery.get_entity_summary(entity_id)
    dashboard_id = arguments.get("dashboard_id")
    view_id = arguments.get("view_id")
    suggestions = _recommended_card_kinds(entity_summary)

    lines = [
        f"Suggest the best supported typed helper cards for entity `{entity_id}`.",
        f"Entity summary: {json.dumps(entity_summary, indent=2)}",
        f"Recommended card kinds in this server: {', '.join(suggestions)}.",
        "Explain which card kind is the best primary choice and which alternative layouts are acceptable.",
        "Include the exact `lovelace.create_card` or `lovelace.update_card` payload you would use.",
    ]
    if isinstance(dashboard_id, str) and dashboard_id:
        lines.append(f"Placement dashboard_id: `{dashboard_id}`.")
    if isinstance(view_id, str) and view_id:
        lines.append(f"Placement view_id: `{view_id}`.")
    if isinstance(dashboard_id, str) and dashboard_id:
        try:
            summary = _dashboard_summary(repository, dashboard_id)
        except KeyError:
            lines.append(
                f"Dashboard `{dashboard_id}` is not currently managed; treat this as a new placement target."
            )
        else:
            lines.append(
                f"Placement dashboard summary: {json.dumps(summary, indent=2)}"
            )
    return _prompt_result(f"Entity card mapping for {entity_id}", lines)


def _dashboard_cleanup_prompt(
    repository: YamlDashboardRepository,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    dashboard_id = _require_string(arguments, "dashboard_id")
    summary = _dashboard_summary(repository, dashboard_id)
    lines = [
        f"Audit dashboard `{dashboard_id}` for cleanup opportunities.",
        f"Dashboard summary: {json.dumps(summary, indent=2)}",
        f"Read `hass://dashboard/{dashboard_id}` and look for redundant views, vague titles, over-nested stacks, and cards that should be consolidated.",
        "Prefer low-risk cleanups that can be expressed as a short sequence of typed `lovelace.*` calls.",
    ]
    return _prompt_result(f"Cleanup audit for {dashboard_id}", lines)


def _dashboard_summary(
    repository: YamlDashboardRepository, dashboard_id: str
) -> dict[str, Any]:
    try:
        dashboard = repository.get_dashboard(dashboard_id)
    except DashboardNotFoundError as err:
        raise KeyError(f"unknown dashboard: {dashboard_id}") from err
    return {
        "dashboard_id": dashboard["metadata"]["dashboard_id"],
        "title": dashboard["metadata"]["title"],
        "url_path": dashboard["metadata"]["url_path"],
        "dashboard_version": dashboard["dashboard_version"],
        "views": _bounded_items(
            [
                {
                    "view_id": view["view_id"],
                    "title": view["title"],
                    "path": view["path"],
                    "card_count": len(view.get("cards", [])),
                }
                for view in dashboard["views"]
            ]
        ),
    }


async def _dashboard_summary_async(
    managed: ManagedDashboardExecutor, dashboard_id: str
) -> dict[str, Any]:
    try:
        dashboard = await managed.get_dashboard(dashboard_id)
    except DashboardNotFoundError as err:
        raise KeyError(f"unknown dashboard: {dashboard_id}") from err
    return {
        "dashboard_id": dashboard["metadata"]["dashboard_id"],
        "title": dashboard["metadata"]["title"],
        "url_path": dashboard["metadata"]["url_path"],
        "dashboard_version": dashboard["dashboard_version"],
        "views": _bounded_items(
            [
                {
                    "view_id": view["view_id"],
                    "title": view["title"],
                    "path": view["path"],
                    "card_count": len(view.get("cards", [])),
                }
                for view in dashboard["views"]
            ]
        ),
    }


def _lookup_area(
    discovery: HomeAssistantDiscoveryProvider, area_id: str
) -> dict[str, Any] | None:
    areas = discovery.list_areas({"limit": 200})
    for area in areas["areas"]:
        if area["area_id"] == area_id:
            return area
    return None


def _recommended_card_kinds(entity_summary: dict[str, Any]) -> tuple[str, ...]:
    domain = entity_summary["domain"]
    device_class = entity_summary.get("device_class")
    if domain == "sensor":
        if device_class in {"temperature", "humidity", "power", "energy"}:
            return ("gauge", "tile", "entities", "glance")
        return ("tile", "entities", "markdown", "glance")
    if domain in {"light", "switch", "fan", "climate", "cover", "lock", "vacuum"}:
        return ("tile", "entities", "glance", "horizontal_stack")
    if domain == "binary_sensor":
        return ("tile", "glance", "entities", "heading")
    return ("tile", "entities", "glance", "markdown")


def _require_string(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value:
        raise KeyError(f"missing prompt argument: {name}")
    return value


def _prompt_result(description: str, lines: list[str]) -> dict[str, Any]:
    return {
        "description": description,
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": "\n".join(lines),
                },
            }
        ],
    }


def _bounded_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    truncated = len(items) > _MAX_PROMPT_SUMMARY_ITEMS
    return {
        "items": items[:_MAX_PROMPT_SUMMARY_ITEMS],
        "truncated": truncated,
    }
