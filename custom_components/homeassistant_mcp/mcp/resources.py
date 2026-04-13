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
from ..frontend_panels import FrontendPanelProvider
from ..lovelace_resources import LovelaceResourceProvider
from ..managed import ManagedDashboardExecutor
from ..native_lovelace import NativeLovelaceProvider
from ..lovelace.errors import DashboardNotFoundError
from ..lovelace.repository import YamlDashboardRepository
from .completions import MAX_COMPLETION_VALUES

ResourceReader = Callable[..., list[dict[str, Any]]]
AsyncResourceReader = Callable[
    ..., list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]
]
ResourceTemplateReader = Callable[
    ..., list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]
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
        return self.read_for_user(uri)

    def read_for_user(
        self, uri: str, *, user: Any | None = None
    ) -> list[dict[str, Any]]:
        """Read one concrete resource by URI for the authenticated user."""
        resource = self._resources.get(uri)
        if resource is not None:
            _definition, reader = resource
            return self._invoke_resource_reader(reader, user=user)

        for binding in self._templates.values():
            match = binding.pattern.fullmatch(uri)
            if match is None or binding.reader is None:
                continue
            return self._invoke_template_reader(
                binding.reader, match.groupdict(), uri, user=user
            )

        raise KeyError(f"unknown resource: {uri}")

    async def async_read(self, uri: str) -> list[dict[str, Any]]:
        """Read one resource by URI, awaiting async readers when needed."""
        return await self.async_read_for_user(uri)

    async def async_read_for_user(
        self, uri: str, *, user: Any | None = None
    ) -> list[dict[str, Any]]:
        """Read one resource by URI for the authenticated user."""
        resource = self._resources.get(uri)
        if resource is not None:
            _definition, reader = resource
            result = self._invoke_resource_reader(reader, user=user)
            if inspect.isawaitable(result):
                result = await result
            return result

        for binding in self._templates.values():
            match = binding.pattern.fullmatch(uri)
            if match is None or binding.reader is None:
                continue
            result = self._invoke_template_reader(
                binding.reader, match.groupdict(), uri, user=user
            )
            if inspect.isawaitable(result):
                result = await result
            return result

        raise KeyError(f"unknown resource: {uri}")

    def _invoke_resource_reader(
        self, reader: AsyncResourceReader, *, user: Any | None = None
    ) -> list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]:
        signature = inspect.signature(reader)
        accepts_user = (
            any(
                parameter.kind == inspect.Parameter.VAR_POSITIONAL
                for parameter in signature.parameters.values()
            )
            or len(signature.parameters) >= 1
        )
        if accepts_user:
            return reader(user)
        return reader()

    def _invoke_template_reader(
        self,
        reader: ResourceTemplateReader,
        params: dict[str, str],
        uri: str,
        *,
        user: Any | None = None,
    ) -> list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]:
        signature = inspect.signature(reader)
        accepts_user = (
            any(
                parameter.kind == inspect.Parameter.VAR_POSITIONAL
                for parameter in signature.parameters.values()
            )
            or len(signature.parameters) >= 3
        )
        if accepts_user:
            return reader(params, uri, user)
        return reader(params, uri)


def register_builtin_resources(
    registry: ResourceRegistry,
    *,
    repository: YamlDashboardRepository,
    discovery: HomeAssistantDiscoveryProvider,
    managed: ManagedDashboardExecutor | None = None,
    native: NativeLovelaceProvider | None = None,
    lovelace_resources: LovelaceResourceProvider | None = None,
    frontend: FrontendPanelProvider | None = None,
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
            lambda user: _native_dashboard_list_resource(native, user=user),
        )
        registry.register_template(
            ResourceTemplateDefinition(
                uri_template="hass://lovelace/dashboard/{url_path}",
                name="Native Lovelace Dashboard",
                description="A native Home Assistant Lovelace dashboard document by url_path.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda params, uri, user: _native_dashboard_resource(
                native, params, uri, user=user
            ),
        )
    if lovelace_resources is not None:
        registry.register(
            ResourceDefinition(
                uri="hass://lovelace/resources",
                name="Lovelace Resources",
                description="Read-only Home Assistant Lovelace resource inventory.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda: _lovelace_resources_list_resource(lovelace_resources),
        )
        registry.register_template(
            ResourceTemplateDefinition(
                uri_template="hass://lovelace/resource/{resource_id}",
                name="Lovelace Resource",
                description="One Home Assistant Lovelace resource by resource identifier.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda params, uri: _lovelace_resource_resource(
                lovelace_resources, params, uri
            ),
        )
    if frontend is not None:
        registry.register(
            ResourceDefinition(
                uri="hass://frontend/panels",
                name="Frontend Panels",
                description="Read-only Home Assistant frontend panels visible to the authenticated user.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda user: _json_resource(
                "hass://frontend/panels",
                frontend.list_panels(user=user, limit=MAX_DISCOVERY_LIMIT),
            ),
        )
        registry.register_template(
            ResourceTemplateDefinition(
                uri_template="hass://frontend/panel/{url_path}",
                name="Frontend Panel",
                description="One Home Assistant frontend panel by url_path, filtered by the authenticated user's permissions.",
                mime_type=_RESOURCE_MIME_TYPE,
            ),
            lambda params, uri, user: _frontend_panel_resource(
                frontend, params, uri, user=user
            ),
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
    *,
    user: Any | None = None,
) -> list[dict[str, Any]]:
    return _json_resource(
        "hass://lovelace/dashboards",
        await native.list_dashboards(user=user, limit=MAX_DISCOVERY_LIMIT),
    )


async def _native_dashboard_resource(
    native: NativeLovelaceProvider,
    params: dict[str, str],
    uri: str,
    *,
    user: Any | None = None,
) -> list[dict[str, Any]]:
    url_path = params.get("url_path")
    if not url_path:
        raise KeyError(f"unknown resource: {uri}")
    try:
        payload = await native.get_dashboard(url_path, user=user)
    except KeyError as err:
        raise KeyError(f"unknown resource: {uri}") from err
    return _json_resource(uri, payload)


async def _lovelace_resources_list_resource(
    provider: LovelaceResourceProvider,
) -> list[dict[str, Any]]:
    return _json_resource(
        "hass://lovelace/resources",
        await provider.list_resources(limit=MAX_DISCOVERY_LIMIT),
    )


async def _lovelace_resource_resource(
    provider: LovelaceResourceProvider,
    params: dict[str, str],
    uri: str,
) -> list[dict[str, Any]]:
    resource_id = params.get("resource_id")
    if not resource_id:
        raise KeyError(f"unknown resource: {uri}")
    try:
        payload = await provider.get_resource(resource_id)
    except KeyError as err:
        raise KeyError(f"unknown resource: {uri}") from err
    return _json_resource(uri, payload)


def _frontend_panel_resource(
    frontend: FrontendPanelProvider,
    params: dict[str, str],
    uri: str,
    *,
    user: Any | None = None,
) -> list[dict[str, Any]]:
    url_path = params.get("url_path")
    if not url_path:
        raise KeyError(f"unknown resource: {uri}")
    try:
        payload = frontend.get_panel(url_path, user=user)
    except KeyError as err:
        raise KeyError(f"unknown resource: {uri}") from err
    return _json_resource(uri, payload)


def _json_resource(uri: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "uri": uri,
            "mimeType": _RESOURCE_MIME_TYPE,
            "text": json.dumps(payload, sort_keys=True, allow_nan=False),
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
