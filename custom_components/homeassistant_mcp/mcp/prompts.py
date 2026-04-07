"""Prompt registry helpers for MCP capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

PromptHandler = Callable[[dict[str, Any]], dict[str, Any]]


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
        return handler(arguments)
