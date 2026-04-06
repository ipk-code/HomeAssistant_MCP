"""Runtime objects for the Home Assistant MCP integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lovelace.repository import YamlDashboardRepository
from .mcp.server import ToolRegistry
from .mcp.transport import StatelessMCPTransport


@dataclass(slots=True)
class IntegrationRuntime:
    """Per-config-entry runtime state."""

    root_path: Path
    repository: YamlDashboardRepository
    registry: ToolRegistry
    transport: StatelessMCPTransport


def create_runtime(root_path: Path) -> IntegrationRuntime:
    """Build repository and transport objects for one config entry."""
    repository = YamlDashboardRepository(root_path)
    registry = ToolRegistry(repository)
    transport = StatelessMCPTransport(registry)
    return IntegrationRuntime(
        root_path=root_path,
        repository=repository,
        registry=registry,
        transport=transport,
    )
