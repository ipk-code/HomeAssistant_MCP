"""Resource registry helpers for MCP capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

ResourceReader = Callable[[], list[dict[str, Any]]]


@dataclass(frozen=True)
class ResourceDefinition:
    """Serializable MCP resource definition."""

    uri: str
    name: str
    description: str
    mime_type: str

    def as_mcp(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass(frozen=True)
class ResourceTemplateDefinition:
    """Serializable MCP resource template definition."""

    uri_template: str
    name: str
    description: str
    mime_type: str

    def as_mcp(self) -> dict[str, Any]:
        return {
            "uriTemplate": self.uri_template,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class ResourceRegistry:
    """Registry for MCP resources and templates."""

    def __init__(self) -> None:
        self._resources: dict[str, tuple[ResourceDefinition, ResourceReader]] = {}
        self._templates: dict[str, ResourceTemplateDefinition] = {}

    def register(self, definition: ResourceDefinition, reader: ResourceReader) -> None:
        """Register a concrete resource and its reader."""
        self._resources[definition.uri] = (definition, reader)

    def register_template(self, definition: ResourceTemplateDefinition) -> None:
        """Register a resource template definition."""
        self._templates[definition.uri_template] = definition

    def list_payload(self) -> dict[str, list[dict[str, Any]]]:
        """Return the MCP `resources/list` payload."""
        return {
            "resources": [
                definition.as_mcp() for definition, _reader in self._resources.values()
            ],
            "resourceTemplates": [
                definition.as_mcp() for definition in self._templates.values()
            ],
        }

    def read(self, uri: str) -> list[dict[str, Any]]:
        """Read one concrete resource by URI."""
        try:
            _definition, reader = self._resources[uri]
        except KeyError as err:
            raise KeyError(f"unknown resource: {uri}") from err
        return reader()
