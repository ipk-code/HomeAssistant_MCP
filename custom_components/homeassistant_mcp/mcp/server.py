"""Tool contract and dispatch helpers for the Home Assistant MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
import json
from pathlib import Path
from typing import Any

from ..discovery import HomeAssistantDiscoveryProvider
from ..lovelace.repository import YamlDashboardRepository
from .schema import ToolSchemaValidator

_API_CONTRACT_FILE = "lovelace_mcp_api_v1.json"


@dataclass(frozen=True)
class ToolContract:
    """Serializable MCP tool contract."""

    name: str
    mutation: bool
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


def _parse_api_contract(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[ToolContract]]:
    """Build the tool-contract objects from a parsed API document."""
    tools = [ToolContract(**tool) for tool in payload["tools"]]
    return payload, tools


@lru_cache(maxsize=1)
def _load_bundled_api_contract() -> tuple[dict[str, Any], list[ToolContract]]:
    """Load the bundled v1 API contract once for the process lifetime."""
    payload = json.loads(
        resources.files("custom_components.homeassistant_mcp")
        .joinpath(_API_CONTRACT_FILE)
        .read_text(encoding="utf-8")
    )
    return _parse_api_contract(payload)


def load_api_contract(
    spec_path: str | Path | None = None,
) -> tuple[dict[str, Any], list[ToolContract]]:
    """Load the static v1 API contract.

    By default, the contract is loaded from the bundled integration package.
    ``spec_path`` remains available for tests and targeted overrides.
    """
    if spec_path is None:
        return _load_bundled_api_contract()

    path = Path(spec_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _parse_api_contract(payload)


class ToolRegistry:
    """Dispatch v1 tool calls against a YAML dashboard repository."""

    def __init__(
        self,
        repository: YamlDashboardRepository,
        discovery: HomeAssistantDiscoveryProvider | None = None,
    ) -> None:
        self._repository = repository
        self._discovery = discovery
        spec, contracts = load_api_contract()
        self._contracts = contracts
        self._validator = ToolSchemaValidator(spec)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return serialized MCP tool definitions."""
        return [
            {
                "name": contract.name,
                "description": contract.description,
                "inputSchema": contract.input_schema,
            }
            for contract in self._contracts
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._validator.validate_tool_arguments(name, arguments)
        if name == "hass.list_entities":
            return self._require_discovery().list_entities(arguments)
        if name == "hass.search_entities":
            return self._require_discovery().search_entities(arguments)
        if name == "hass.list_services":
            return self._require_discovery().list_services(arguments)
        if name == "hass.list_areas":
            return self._require_discovery().list_areas(arguments)
        if name == "hass.list_devices":
            return self._require_discovery().list_devices(arguments)
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
                "view": self._repository.get_view(
                    arguments["dashboard_id"], arguments["view_id"]
                ),
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
                "cards": self._repository.list_cards(
                    arguments["dashboard_id"], arguments["view_id"]
                ),
            }
        if name == "lovelace.get_card":
            return {
                "dashboard_id": arguments["dashboard_id"],
                "view_id": arguments["view_id"],
                "card": self._repository.get_card(
                    arguments["dashboard_id"],
                    arguments["view_id"],
                    arguments["card_id"],
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

    def _require_discovery(self) -> HomeAssistantDiscoveryProvider:
        if self._discovery is None:
            raise KeyError("Home Assistant discovery provider is unavailable")
        return self._discovery
