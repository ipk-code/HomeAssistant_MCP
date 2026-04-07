"""Resource registry helpers for MCP capabilities."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import json
import re
from typing import Any, Awaitable, Callable

from ..const import (
    DEFAULT_DASHBOARD_MODE,
    DEFAULT_TRANSPORT,
    DOMAIN,
    INTEGRATION_VERSION,
    STREAMABLE_HTTP_API,
    TITLE,
)
from ..discovery import (
    DEFAULT_DISCOVERY_LIMIT,
    HomeAssistantDiscoveryProvider,
    MAX_DISCOVERY_LIMIT,
)
from ..managed import ManagedDashboardExecutor
from ..native_lovelace import NativeLovelaceProvider
from ..lovelace.errors import DashboardNotFoundError
from ..lovelace.repository import YamlDashboardRepository
from .completions import MAX_COMPLETION_VALUES

ResourceReader = Callable[[], list[dict[str, Any]]]
AsyncResourceReader = Callable[
    [], list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]
]
ResourceTemplateReader = Callable[
    [dict[str, str], str], list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]
]


_RESOURCE_MIME_TYPE = "application/json"


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


@dataclass(frozen=True)
class _ResourceTemplateBinding:
    """Template binding with compiled matching metadata."""

    definition: ResourceTemplateDefinition
    reader: ResourceTemplateReader | None
    pattern: re.Pattern[str]
    parameter_names: tuple[str, ...]


class ResourceRegistry:
    """Registry for MCP resources and templates."""

    def __init__(self) -> None:
        self._resources: dict[str, tuple[ResourceDefinition, ResourceReader]] = {}
        self._templates: dict[str, _ResourceTemplateBinding] = {}

    def register(
        self, definition: ResourceDefinition, reader: AsyncResourceReader
    ) -> None:
        """Register a concrete resource and its reader."""
        self._resources[definition.uri] = (definition, reader)

    def register_template(
        self,
        definition: ResourceTemplateDefinition,
        reader: ResourceTemplateReader | None = None,
    ) -> None:
        """Register a resource template definition and optional reader."""
        pattern, parameter_names = _compile_uri_template(definition.uri_template)
        self._templates[definition.uri_template] = _ResourceTemplateBinding(
            definition=definition,
            reader=reader,
            pattern=pattern,
            parameter_names=parameter_names,
        )

    def list_payload(self) -> dict[str, list[dict[str, Any]]]:
        """Return the MCP `resources/list` payload."""
        return {
            "resources": [
                definition.as_mcp() for definition, _reader in self._resources.values()
            ],
            "resourceTemplates": [
                binding.definition.as_mcp() for binding in self._templates.values()
            ],
        }

    def read(self, uri: str) -> list[dict[str, Any]]:
        """Read one concrete resource by URI."""
        resource = self._resources.get(uri)
        if resource is not None:
            _definition, reader = resource
            return reader()

        for binding in self._templates.values():
            match = binding.pattern.fullmatch(uri)
            if match is None or binding.reader is None:
                continue
            return binding.reader(match.groupdict(), uri)

        raise KeyError(f"unknown resource: {uri}")

    async def async_read(self, uri: str) -> list[dict[str, Any]]:
        """Read one resource by URI, awaiting async readers when needed."""
        resource = self._resources.get(uri)
        if resource is not None:
            _definition, reader = resource
            result = reader()
            if inspect.isawaitable(result):
                result = await result
            return result

        for binding in self._templates.values():
            match = binding.pattern.fullmatch(uri)
            if match is None or binding.reader is None:
                continue
            result = binding.reader(match.groupdict(), uri)
            if inspect.isawaitable(result):
                result = await result
            return result

        raise KeyError(f"unknown resource: {uri}")


def register_builtin_resources(
    registry: ResourceRegistry,
    *,
    repository: YamlDashboardRepository,
    discovery: HomeAssistantDiscoveryProvider,
    managed: ManagedDashboardExecutor | None = None,
    native: NativeLovelaceProvider | None = None,
) -> None:
    """Register the built-in Home Assistant MCP resources."""
    registry.register(
        ResourceDefinition(
            uri="hass://config",
            name="Home Assistant MCP Config",
            description="Current integration transport, auth, and default runtime settings.",
            mime_type=_RESOURCE_MIME_TYPE,
        ),
        lambda: _json_resource(
            "hass://config",
            {
                "integration": {
                    "domain": DOMAIN,
                    "title": TITLE,
                    "version": INTEGRATION_VERSION,
                },
                "transport": {
                    "endpoint": STREAMABLE_HTTP_API,
                    "mode": DEFAULT_TRANSPORT,
                    "requires_auth": True,
                },
                "defaults": {
                    "dashboard_mode": DEFAULT_DASHBOARD_MODE,
                    "discovery_default_limit": DEFAULT_DISCOVERY_LIMIT,
                    "discovery_max_limit": MAX_DISCOVERY_LIMIT,
                    "completion_max_values": MAX_COMPLETION_VALUES,
                },
            },
        ),
    )
    registry.register(
        ResourceDefinition(
            uri="hass://entities",
            name="Home Assistant Entities",
            description="Bounded read-only entity inventory used by the discovery tools.",
            mime_type=_RESOURCE_MIME_TYPE,
        ),
        lambda: _json_resource(
            "hass://entities",
            discovery.list_entities({"limit": MAX_DISCOVERY_LIMIT}),
        ),
    )
    registry.register(
        ResourceDefinition(
            uri="hass://areas",
            name="Home Assistant Areas",
            description="Configured Home Assistant areas.",
            mime_type=_RESOURCE_MIME_TYPE,
        ),
        lambda: _json_resource(
            "hass://areas",
            discovery.list_areas({"limit": MAX_DISCOVERY_LIMIT}),
        ),
    )
    registry.register(
        ResourceDefinition(
            uri="hass://devices",
            name="Home Assistant Devices",
            description="Bounded read-only Home Assistant device inventory.",
            mime_type=_RESOURCE_MIME_TYPE,
        ),
        lambda: _json_resource(
            "hass://devices",
            discovery.list_devices({"limit": MAX_DISCOVERY_LIMIT}),
        ),
    )
    registry.register(
        ResourceDefinition(
            uri="hass://services",
            name="Home Assistant Services",
            description="Registered Home Assistant services grouped by domain.",
            mime_type=_RESOURCE_MIME_TYPE,
        ),
        lambda: _json_resource(
            "hass://services",
            discovery.list_services({"limit": MAX_DISCOVERY_LIMIT}),
        ),
    )
    registry.register_template(
        ResourceTemplateDefinition(
            uri_template="hass://dashboard/{dashboard_id}",
            name="Managed Dashboard",
            description="A managed Lovelace dashboard document by dashboard identifier.",
            mime_type=_RESOURCE_MIME_TYPE,
        ),
        (
            (lambda params, uri: _dashboard_resource_async(managed, params, uri))
            if managed is not None
            else lambda params, uri: _dashboard_resource(repository, params, uri)
        ),
    )
    if native is not None:
        registry.register(
            ResourceDefinition(
                uri="hass://lovelace/dashboards",
                name="Native Lovelace Dashboards",
                description="Read-only Home Assistant Lovelace dashboards outside the MCP-managed repository.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda: _native_dashboard_list_resource(native),
        )
        registry.register_template(
            ResourceTemplateDefinition(
                uri_template="hass://lovelace/dashboard/{url_path}",
                name="Native Lovelace Dashboard",
                description="A native Home Assistant Lovelace dashboard document by url_path.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda params, uri: _native_dashboard_resource(native, params, uri),
        )


def _dashboard_resource(
    repository: YamlDashboardRepository,
    params: dict[str, str],
    uri: str,
) -> list[dict[str, Any]]:
    dashboard_id = params.get("dashboard_id")
    if not dashboard_id:
        raise KeyError(f"unknown resource: {uri}")
    try:
        payload = repository.get_dashboard(dashboard_id)
    except DashboardNotFoundError as err:
        raise KeyError(f"unknown resource: {uri}") from err
    return _json_resource(uri, payload)


async def _dashboard_resource_async(
    managed: ManagedDashboardExecutor,
    params: dict[str, str],
    uri: str,
) -> list[dict[str, Any]]:
    dashboard_id = params.get("dashboard_id")
    if not dashboard_id:
        raise KeyError(f"unknown resource: {uri}")
    try:
        payload = await managed.get_dashboard(dashboard_id)
    except (DashboardNotFoundError, Exception) as err:
        raise KeyError(f"unknown resource: {uri}") from err
    return _json_resource(uri, payload)


async def _native_dashboard_list_resource(
    native: NativeLovelaceProvider,
) -> list[dict[str, Any]]:
    return _json_resource(
        "hass://lovelace/dashboards",
        await native.list_dashboards(limit=MAX_DISCOVERY_LIMIT),
    )


async def _native_dashboard_resource(
    native: NativeLovelaceProvider,
    params: dict[str, str],
    uri: str,
) -> list[dict[str, Any]]:
    url_path = params.get("url_path")
    if not url_path:
        raise KeyError(f"unknown resource: {uri}")
    try:
        payload = await native.get_dashboard(url_path)
    except KeyError as err:
        raise KeyError(f"unknown resource: {uri}") from err
    return _json_resource(uri, payload)


def _json_resource(uri: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "uri": uri,
            "mimeType": _RESOURCE_MIME_TYPE,
            "text": json.dumps(payload, sort_keys=True),
        }
    ]


def _compile_uri_template(uri_template: str) -> tuple[re.Pattern[str], tuple[str, ...]]:
    parameter_names = tuple(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", uri_template))
    pattern = re.escape(uri_template)
    for parameter_name in parameter_names:
        pattern = pattern.replace(
            re.escape("{" + parameter_name + "}"),
            rf"(?P<{parameter_name}>[^/]+)",
        )
    return re.compile(rf"^{pattern}$"), parameter_names
