"""Tool contract and dispatch helpers for the Home Assistant MCP server."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ..lovelace.repository import YamlDashboardRepository
from .schema import ToolSchemaValidator


@dataclass(frozen=True)
class ToolContract:
    """Serializable MCP tool contract."""

    name: str
    mutation: bool
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


def load_api_contract(spec_path: str | Path | None = None) -> tuple[dict[str, Any], list[ToolContract]]:
    """Load the static v1 API contract from the repository spec."""
    path = Path(spec_path) if spec_path else Path(__file__).resolve().parents[3] / "specs" / "lovelace_mcp_api_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    tools = [ToolContract(**tool) for tool in payload["tools"]]
    return payload, tools


class ToolRegistry:
    """Dispatch v1 tool calls against a YAML dashboard repository."""

    def __init__(self, repository: YamlDashboardRepository) -> None:
        self._repository = repository
        spec, _ = load_api_contract()
        self._validator = ToolSchemaValidator(spec)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._validator.validate_tool_arguments(name, arguments)
        if name == "lovelace.list_dashboards":
            return {"dashboards": self._repository.list_dashboards()}
        if name == "lovelace.get_dashboard":
            return self._repository.get_dashboard(arguments["dashboard_id"])
        if name == "lovelace.create_dashboard":
            return self._repository.create_dashboard(arguments)
        if name == "lovelace.update_dashboard_metadata":
            return self._repository.update_dashboard_metadata(
                arguments["dashboard_id"],
                arguments["metadata"],
                expected_version=arguments.get("expected_version"),
            )
        if name == "lovelace.delete_dashboard":
            return self._repository.delete_dashboard(
                arguments["dashboard_id"],
                expected_version=arguments.get("expected_version"),
            )
        if name == "lovelace.list_views":
            return {
                "dashboard_id": arguments["dashboard_id"],
                "views": self._repository.list_views(arguments["dashboard_id"]),
            }
        if name == "lovelace.get_view":
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view": self._repository.get_view(arguments["dashboard_id"], arguments["view_id"]),
            }
        if name == "lovelace.create_view":
            view, version = self._repository.create_view(
                arguments["dashboard_id"],
                arguments["view"],
                position=arguments.get("position"),
                expected_version=arguments.get("expected_version"),
            )
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view": view,
                "dashboard_version": version,
            }
        if name == "lovelace.update_view":
            view, version = self._repository.update_view(
                arguments["dashboard_id"],
                arguments["view_id"],
                arguments["view"],
                position=arguments.get("position"),
                expected_version=arguments.get("expected_version"),
            )
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view": view,
                "dashboard_version": version,
            }
        if name == "lovelace.delete_view":
            return self._repository.delete_view(
                arguments["dashboard_id"],
                arguments["view_id"],
                expected_version=arguments.get("expected_version"),
            )
        if name == "lovelace.list_cards":
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view_id": arguments["view_id"],
                "cards": self._repository.list_cards(arguments["dashboard_id"], arguments["view_id"]),
            }
        if name == "lovelace.get_card":
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view_id": arguments["view_id"],
                "card": self._repository.get_card(
                    arguments["dashboard_id"], arguments["view_id"], arguments["card_id"]
                ),
            }
        if name == "lovelace.create_card":
            card, version = self._repository.create_card(
                arguments["dashboard_id"],
                arguments["view_id"],
                arguments["card"],
                position=arguments.get("position"),
                expected_version=arguments.get("expected_version"),
            )
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view_id": arguments["view_id"],
                "card": card,
                "dashboard_version": version,
            }
        if name == "lovelace.update_card":
            card, version = self._repository.update_card(
                arguments["dashboard_id"],
                arguments["view_id"],
                arguments["card_id"],
                arguments["card"],
                expected_version=arguments.get("expected_version"),
            )
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view_id": arguments["view_id"],
                "card": card,
                "dashboard_version": version,
            }
        if name == "lovelace.delete_card":
            return self._repository.delete_card(
                arguments["dashboard_id"],
                arguments["view_id"],
                arguments["card_id"],
                expected_version=arguments.get("expected_version"),
            )
        if name == "lovelace.patch_dashboard":
            dashboard, applied = self._repository.patch_dashboard(
                arguments["dashboard_id"],
                arguments["operations"],
                expected_version=arguments.get("expected_version"),
            )
            return {"dashboard": dashboard, "applied_operations": applied}
        if name == "lovelace.validate_dashboard":
            if "dashboard" in arguments:
                normalized = self._repository.validate_dashboard(arguments["dashboard"])
            else:
                normalized = self._repository.validate_patch(
                    arguments["dashboard_id"], arguments["operations"]
                )
            return {
                "valid": True,
                "normalized_dashboard": normalized,
                "errors": [],
                "warnings": [],
            }
        raise KeyError(f"unknown tool: {name}")
