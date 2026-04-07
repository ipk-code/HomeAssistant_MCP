"""Runtime objects for the Home Assistant MCP integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from .discovery import HomeAssistantDiscoveryProvider
from .lovelace.repository import YamlDashboardRepository
from .mcp.completions import CompletionRegistry, register_builtin_completions
from .mcp.prompts import PromptRegistry
from .mcp.resources import ResourceRegistry
from .mcp.server import ToolRegistry
from .mcp.transport import StatelessMCPTransport

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class IntegrationRuntime:
    """Per-config-entry runtime state."""

    root_path: Path
    repository: YamlDashboardRepository
    discovery: HomeAssistantDiscoveryProvider
    registry: ToolRegistry
    resources: ResourceRegistry
    prompts: PromptRegistry
    completions: CompletionRegistry
    transport: StatelessMCPTransport


def create_runtime(hass: Any, root_path: Path) -> IntegrationRuntime:
    """Build repository and transport objects for one config entry."""
    _LOGGER.debug("Creating Home Assistant MCP runtime at %s", root_path)
    repository = YamlDashboardRepository(root_path)
    discovery = HomeAssistantDiscoveryProvider(hass)
    registry = ToolRegistry(repository, discovery=discovery)
    resources = ResourceRegistry()
    prompts = PromptRegistry()
    completions = CompletionRegistry()
    register_builtin_completions(
        completions,
        repository=repository,
        discovery=discovery,
    )
    transport = StatelessMCPTransport(
        registry,
        resources=resources,
        prompts=prompts,
        completions=completions,
    )
    return IntegrationRuntime(
        root_path=root_path,
        repository=repository,
        discovery=discovery,
        registry=registry,
        resources=resources,
        prompts=prompts,
        completions=completions,
        transport=transport,
    )
