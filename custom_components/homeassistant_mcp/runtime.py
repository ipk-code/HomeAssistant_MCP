"""Runtime objects for the Home Assistant MCP integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from .const import ADMIN_REQUIRED_TOOLS
from .discovery import HomeAssistantDiscoveryProvider
from .frontend_panels import FrontendPanelProvider
from .managed import ManagedDashboardExecutor
from .lovelace_resources import LovelaceResourceProvider
from .lovelace.repository import YamlDashboardRepository
from .mcp.completions import CompletionRegistry, register_builtin_completions
from .mcp.prompts import PromptRegistry, register_builtin_prompts
from .mcp.resources import ResourceRegistry, register_builtin_resources
from .mcp.server import ToolRegistry
from .mcp.transport import StatelessMCPTransport
from .native_lovelace import NativeLovelaceProvider
from .template_sensors import TemplateSensorProvider

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class IntegrationRuntime:
    """Per-config-entry runtime state."""

    root_path: Path
    repository: YamlDashboardRepository
    managed: ManagedDashboardExecutor
    native_lovelace: NativeLovelaceProvider
    lovelace_resources: LovelaceResourceProvider
    frontend_panels: FrontendPanelProvider
    template_sensors: TemplateSensorProvider
    discovery: HomeAssistantDiscoveryProvider
    registry: ToolRegistry
    resources: ResourceRegistry
    prompts: PromptRegistry
    completions: CompletionRegistry
    transport: StatelessMCPTransport


def create_runtime(
    hass: Any, root_path: Path, *, admin_functions_enabled: bool = False
) -> IntegrationRuntime:
    """Build repository and transport objects for one config entry."""
    _LOGGER.debug("Creating Home Assistant MCP runtime at %s", root_path)
    repository = YamlDashboardRepository(root_path)
    managed = ManagedDashboardExecutor(hass, repository)
    native_lovelace = NativeLovelaceProvider(hass)
    lovelace_resources = LovelaceResourceProvider(hass)
    frontend_panels = FrontendPanelProvider(hass)
    template_sensors = TemplateSensorProvider(hass)
    discovery = HomeAssistantDiscoveryProvider(hass)
    registry = ToolRegistry(repository, discovery=discovery)
    resources = ResourceRegistry()
    register_builtin_resources(
        resources,
        repository=repository,
        discovery=discovery,
        managed=managed,
        native=native_lovelace,
        lovelace_resources=lovelace_resources,
        frontend=frontend_panels,
    )
    prompts = PromptRegistry()
    register_builtin_prompts(
        prompts,
        repository=repository,
        discovery=discovery,
        managed=managed,
    )
    completions = CompletionRegistry()
    register_builtin_completions(
        completions,
        repository=repository,
        discovery=discovery,
        managed=managed,
    )
    transport = StatelessMCPTransport(
        registry,
        resources=resources,
        prompts=prompts,
        completions=completions,
        managed=managed,
        native_lovelace=native_lovelace,
        lovelace_resources=lovelace_resources,
        frontend_panels=frontend_panels,
        template_sensors=template_sensors,
        admin_functions_enabled=admin_functions_enabled,
        admin_required_tools=ADMIN_REQUIRED_TOOLS,
    )
    return IntegrationRuntime(
        root_path=root_path,
        repository=repository,
        managed=managed,
        native_lovelace=native_lovelace,
        lovelace_resources=lovelace_resources,
        frontend_panels=frontend_panels,
        template_sensors=template_sensors,
        discovery=discovery,
        registry=registry,
        resources=resources,
        prompts=prompts,
        completions=completions,
        transport=transport,
    )
