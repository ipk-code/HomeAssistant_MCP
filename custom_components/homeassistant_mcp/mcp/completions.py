"""Completion registry helpers for MCP capabilities."""

from __future__ import annotations

from typing import Any, Callable

CompletionProvider = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


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
        return provider(ref, argument)
