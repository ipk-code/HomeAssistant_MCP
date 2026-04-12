"""Stateless Streamable HTTP transport helpers for MCP requests."""

from __future__ import annotations

from http import HTTPStatus
import json
import logging
from typing import Any

from ..const import API_VERSION, MAX_REQUEST_BYTES, TITLE
from ..frontend_panels import FrontendPanelProvider
from ..lovelace_resources import LovelaceResourceProvider
from ..managed import ManagedDashboardExecutor
from ..lovelace.errors import LovelaceMCPError
from ..native_lovelace import NativeLovelaceProvider
from .completions import CompletionRegistry
from .prompts import PromptRegistry
from .resources import ResourceRegistry
from .schema import ToolSchemaValidationError
from .server import ToolRegistry

CONTENT_TYPE_JSON = "application/json"
_LOGGER = logging.getLogger(__name__)


def _s(value: Any) -> str:
    """Sanitize a value for safe log inclusion (CWE-117: log injection).

    Strips all ASCII control characters (0x00-0x1F, 0x7F) so that a
    malicious client cannot inject fake log lines via CR/LF, corrupt
    terminal output via ANSI escape sequences (ESC = 0x1B), or embed
    null bytes that truncate log entries in certain log aggregators.
    """
    text = str(value)
    return "".join(
        ch if 0x20 <= ord(ch) < 0x7F or ord(ch) > 0x7F else f"\\x{ord(ch):02x}"
        for ch in text
    )


def _accepts_json(accept: str) -> bool:
    """Return True if the Accept header includes application/json or */*.

    Uses exact media-type token comparison after splitting on commas and
    stripping quality parameters. A naive ``in`` substring check would
    accept ``application/json-patch+json`` as a match for
    ``application/json``, producing a false positive.
    """
    for part in accept.split(","):
        media_type = part.split(";", 1)[0].strip().lower()
        if media_type in {CONTENT_TYPE_JSON, "*/*", "application/*"}:
            return True
    return False


class StatelessMCPTransport:
    """Minimal stateless MCP transport facade over the tool registry."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        resources: ResourceRegistry | None = None,
        prompts: PromptRegistry | None = None,
        completions: CompletionRegistry | None = None,
        managed: ManagedDashboardExecutor | None = None,
        native_lovelace: NativeLovelaceProvider | None = None,
        lovelace_resources: LovelaceResourceProvider | None = None,
        frontend_panels: FrontendPanelProvider | None = None,
    ) -> None:
        self._registry = registry
        self._resources = resources or ResourceRegistry()
        self._prompts = prompts or PromptRegistry()
        self._completions = completions or CompletionRegistry()
        self._managed = managed
        self._native_lovelace = native_lovelace
        self._lovelace_resources = lovelace_resources
        self._frontend_panels = frontend_panels

    def handle_http_request(
        self, *, accept: str, content_type: str, body: str, user: Any | None = None
    ) -> tuple[int, dict[str, Any] | None]:
        """Validate an HTTP request and dispatch a JSON-RPC message."""
        if not _accepts_json(accept):
            _LOGGER.warning("Rejected MCP request because Accept header is invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, f"Client must accept {CONTENT_TYPE_JSON}"
            )
        if content_type != CONTENT_TYPE_JSON:
            _LOGGER.warning("Rejected MCP request because Content-Type is invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, f"Content-Type must be {CONTENT_TYPE_JSON}"
            )
        if len(body.encode("utf-8")) > MAX_REQUEST_BYTES:
            _LOGGER.warning(
                "Rejected MCP request because body exceeded %s bytes", MAX_REQUEST_BYTES
            )
            return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, self._jsonrpc_error(
                None, -32013, "Request body exceeds maximum size"
            )
        try:
            message = json.loads(body)
        except json.JSONDecodeError:
            _LOGGER.warning("Rejected MCP request because body was not valid JSON")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32700, "Request body must be valid JSON"
            )
        return self.handle_jsonrpc_message(message, user=user)

    async def handle_http_request_async(
        self,
        *,
        accept: str,
        content_type: str,
        body: str,
        user: Any | None = None,
    ) -> tuple[int, dict[str, Any] | None]:
        """Async HTTP request handling for request paths that may use executors."""
        if not _accepts_json(accept):
            _LOGGER.warning("Rejected MCP request because Accept header is invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, f"Client must accept {CONTENT_TYPE_JSON}"
            )
        if content_type != CONTENT_TYPE_JSON:
            _LOGGER.warning("Rejected MCP request because Content-Type is invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, f"Content-Type must be {CONTENT_TYPE_JSON}"
            )
        if len(body.encode("utf-8")) > MAX_REQUEST_BYTES:
            _LOGGER.warning(
                "Rejected MCP request because body exceeded %s bytes", MAX_REQUEST_BYTES
            )
            return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, self._jsonrpc_error(
                None, -32013, "Request body exceeds maximum size"
            )
        try:
            message = json.loads(body)
        except json.JSONDecodeError:
            _LOGGER.warning("Rejected MCP request because body was not valid JSON")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32700, "Request body must be valid JSON"
            )
        return await self.handle_jsonrpc_message_async(message, user=user)

    def handle_jsonrpc_message(
        self, message: dict[str, Any], user: Any | None = None
    ) -> tuple[int, dict[str, Any] | None]:
        """Handle a single JSON-RPC request in stateless mode."""
        if not isinstance(message, dict):
            _LOGGER.warning(
                "Rejected MCP request because JSON-RPC payload was not an object"
            )
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, "JSON-RPC request must be an object"
            )
        if message.get("jsonrpc") != "2.0":
            _LOGGER.warning("Rejected MCP request because jsonrpc version was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32600, "jsonrpc must be '2.0'"
            )

        method = message.get("method")
        params = message.get("params")
        if params is None:
            params = {}

        if not isinstance(method, str):
            _LOGGER.warning("Rejected MCP request because method was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32600, "method must be a string"
            )
        if not isinstance(params, dict):
            _LOGGER.warning("Rejected MCP request because params was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32602, "params must be an object"
            )

        request_id = message.get("id")
        if request_id is None:
            _LOGGER.debug("Accepted MCP notification for method %s", _s(method))
            return HTTPStatus.ACCEPTED, None

        if method == "initialize":
            _LOGGER.debug("Handled MCP initialize request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "1.0"),
                    "serverInfo": {"name": TITLE, "version": API_VERSION},
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                },
            }

        if method == "ping":
            _LOGGER.debug("Handled MCP ping request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {},
            }

        if method == "tools/list":
            _LOGGER.debug("Handled MCP tools/list request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self._registry.list_tools()},
            }

        if method == "resources/list":
            _LOGGER.debug("Handled MCP resources/list request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self._resources.list_payload(),
            }

        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str):
                _LOGGER.warning(
                    "Rejected MCP resources/read request %s because uri was invalid",
                    request_id,
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "resources/read requires a string uri"
                )
            try:
                _LOGGER.debug(
                    "Reading MCP resource %s for request %s", _s(uri), _s(request_id)
                )
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "contents": self._resources.read_for_user(uri, user=user)
                    },
                }
            except KeyError as err:
                _LOGGER.debug(
                    "Rejected MCP resources/read request %s because resource %s was unknown: %s",
                    _s(request_id),
                    _s(uri),
                    _s(err),
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, str(err)
                )

        if method == "prompts/list":
            _LOGGER.debug("Handled MCP prompts/list request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"prompts": self._prompts.list_prompts()},
            }

        if method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(prompt_name, str) or not isinstance(arguments, dict):
                _LOGGER.warning(
                    "Rejected MCP prompts/get request %s because name or arguments were invalid",
                    request_id,
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "prompts/get requires name and arguments"
                )
            try:
                _LOGGER.debug(
                    "Handled MCP prompts/get request %s for %s",
                    _s(request_id),
                    _s(prompt_name),
                )
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": self._prompts.get(prompt_name, arguments),
                }
            except KeyError as err:
                _LOGGER.warning(
                    "Rejected MCP prompts/get request %s because prompt %s was unknown",
                    _s(request_id),
                    _s(prompt_name),
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, str(err)
                )

        if method == "completion/complete":
            ref = params.get("ref")
            if ref is None:
                ref = {}
            argument = params.get("argument")
            if argument is None:
                argument = {}
            if not isinstance(ref, dict) or not isinstance(argument, dict):
                _LOGGER.warning(
                    "Rejected MCP completion/complete request %s because ref or argument were invalid",
                    request_id,
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id,
                    -32602,
                    "completion/complete requires ref and argument objects",
                )
            _LOGGER.debug("Handled MCP completion/complete request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"completion": self._completions.complete(ref, argument)},
            }

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                _LOGGER.warning(
                    "Rejected MCP tools/call request %s because name or arguments were invalid",
                    _s(request_id),
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "tools/call requires name and arguments"
                )
            try:
                _LOGGER.debug(
                    "Executing MCP tool %s for request %s", _s(tool_name), _s(request_id)
                )
                payload = self._call_tool(tool_name, arguments, user=user)
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(payload)}],
                        "isError": False,
                    },
                }
            except (KeyError, LovelaceMCPError, ToolSchemaValidationError) as err:
                _LOGGER.warning(
                    "MCP tool %s failed validation or execution for request %s: %s",
                    _s(tool_name),
                    _s(request_id),
                    _s(err),
                )
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": str(err)}],
                        "isError": True,
                    },
                }
            except Exception:
                _LOGGER.exception(
                    "Unexpected MCP transport failure for tool %s request %s",
                    _s(tool_name),
                    _s(request_id),
                )
                return HTTPStatus.INTERNAL_SERVER_ERROR, self._jsonrpc_error(
                    request_id, -32603, "Internal server error"
                )

        _LOGGER.warning(
            "Rejected MCP request %s because method %s is unknown",
            _s(request_id),
            _s(method),
        )
        return HTTPStatus.NOT_FOUND, self._jsonrpc_error(
            request_id, -32601, f"Unknown method: {method}"
        )

    async def handle_jsonrpc_message_async(
        self, message: dict[str, Any], user: Any | None = None
    ) -> tuple[int, dict[str, Any] | None]:
        """Handle a single JSON-RPC request with async support for blocking paths."""
        if not isinstance(message, dict):
            _LOGGER.warning(
                "Rejected MCP request because JSON-RPC payload was not an object"
            )
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, "JSON-RPC request must be an object"
            )
        if message.get("jsonrpc") != "2.0":
            _LOGGER.warning("Rejected MCP request because jsonrpc version was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32600, "jsonrpc must be '2.0'"
            )

        method = message.get("method")
        params = message.get("params")
        if params is None:
            params = {}

        if not isinstance(method, str):
            _LOGGER.warning("Rejected MCP request because method was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32600, "method must be a string"
            )
        if not isinstance(params, dict):
            _LOGGER.warning("Rejected MCP request because params was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32602, "params must be an object"
            )

        if method in {
            "initialize",
            "ping",
            "tools/list",
            "resources/list",
            "prompts/list",
        }:
            return self.handle_jsonrpc_message(message, user=user)

        request_id = message.get("id")
        if request_id is None:
            _LOGGER.debug("Accepted MCP notification for method %s", _s(method))
            return HTTPStatus.ACCEPTED, None

        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str):
                _LOGGER.warning(
                    "Rejected MCP resources/read request %s because uri was invalid",
                    request_id,
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "resources/read requires a string uri"
                )
            try:
                _LOGGER.debug(
                    "Reading MCP resource %s for request %s", _s(uri), _s(request_id)
                )
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "contents": await self._resources.async_read_for_user(
                            uri, user=user
                        )
                    },
                }
            except (KeyError, LovelaceMCPError) as err:
                _LOGGER.debug(
                    "Rejected MCP resources/read request %s because resource %s was invalid or unknown: %s",
                    _s(request_id),
                    _s(uri),
                    _s(err),
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, str(err)
                )

        if method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(prompt_name, str) or not isinstance(arguments, dict):
                _LOGGER.warning(
                    "Rejected MCP prompts/get request %s because name or arguments were invalid",
                    request_id,
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "prompts/get requires name and arguments"
                )
            try:
                _LOGGER.debug(
                    "Handled MCP prompts/get request %s for %s",
                    _s(request_id),
                    _s(prompt_name),
                )
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": await self._prompts.async_get(prompt_name, arguments),
                }
            except (KeyError, LovelaceMCPError) as err:
                _LOGGER.warning(
                    "Rejected MCP prompts/get request %s because prompt %s failed: %s",
                    _s(request_id),
                    _s(prompt_name),
                    _s(err),
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, str(err)
                )

        if method == "completion/complete":
            ref = params.get("ref")
            if ref is None:
                ref = {}
            argument = params.get("argument")
            if argument is None:
                argument = {}
            if not isinstance(ref, dict) or not isinstance(argument, dict):
                _LOGGER.warning(
                    "Rejected MCP completion/complete request %s because ref or argument were invalid",
                    request_id,
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id,
                    -32602,
                    "completion/complete requires ref and argument objects",
                )
            _LOGGER.debug("Handled MCP completion/complete request %s", _s(request_id))
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "completion": await self._completions.async_complete(ref, argument)
                },
            }

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                _LOGGER.warning(
                    "Rejected MCP tools/call request %s because name or arguments were invalid",
                    _s(request_id),
                )
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "tools/call requires name and arguments"
                )
            try:
                _LOGGER.debug(
                    "Executing MCP tool %s for request %s", _s(tool_name), _s(request_id)
                )
                payload = await self._async_call_tool(tool_name, arguments, user=user)
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(payload)}],
                        "isError": False,
                    },
                }
            except (KeyError, LovelaceMCPError, ToolSchemaValidationError) as err:
                _LOGGER.warning(
                    "MCP tool %s failed validation or execution for request %s: %s",
                    _s(tool_name),
                    _s(request_id),
                    _s(err),
                )
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": str(err)}],
                        "isError": True,
                    },
                }
            except Exception:
                _LOGGER.exception(
                    "Unexpected MCP transport failure for tool %s request %s",
                    _s(tool_name),
                    _s(request_id),
                )
                return HTTPStatus.INTERNAL_SERVER_ERROR, self._jsonrpc_error(
                    request_id, -32603, "Internal server error"
                )

        _LOGGER.warning(
            "Rejected MCP request %s because method %s is unknown",
            _s(request_id),
            _s(method),
        )
        return HTTPStatus.NOT_FOUND, self._jsonrpc_error(
            request_id, -32601, f"Unknown method: {method}"
        )

    def _call_tool(
        self, tool_name: str, arguments: dict[str, Any], *, user: Any | None = None
    ) -> dict[str, Any]:
        if tool_name == "hass.list_frontend_panels":
            self._registry.validate_arguments(tool_name, arguments)
            if self._frontend_panels is None:
                raise KeyError("frontend panel provider is unavailable")
            limit = arguments.get("limit", 100)
            return self._frontend_panels.list_panels(user=user, limit=limit)
        if tool_name == "hass.get_frontend_panel":
            self._registry.validate_arguments(tool_name, arguments)
            if self._frontend_panels is None:
                raise KeyError("frontend panel provider is unavailable")
            return {
                "panel": self._frontend_panels.get_panel(
                    arguments["url_path"], user=user
                )
            }
        return self._registry.call(tool_name, arguments)

    async def _async_call_tool(
        self, tool_name: str, arguments: dict[str, Any], *, user: Any | None = None
    ) -> dict[str, Any]:
        if tool_name in {"hass.list_frontend_panels", "hass.get_frontend_panel"}:
            return self._call_tool(tool_name, arguments, user=user)
        if tool_name == "hass.list_lovelace_dashboards":
            self._registry.validate_arguments(tool_name, arguments)
            if self._native_lovelace is None:
                raise KeyError("native lovelace provider is unavailable")
            limit = arguments.get("limit", 100)
            return await self._native_lovelace.list_dashboards(user=user, limit=limit)
        if tool_name == "hass.get_lovelace_dashboard":
            self._registry.validate_arguments(tool_name, arguments)
            if self._native_lovelace is None:
                raise KeyError("native lovelace provider is unavailable")
            return {
                "dashboard": await self._native_lovelace.get_dashboard(
                    arguments["url_path"], user=user
                )
            }
        if tool_name == "hass.create_lovelace_dashboard":
            self._registry.validate_arguments(tool_name, arguments)
            if self._native_lovelace is None:
                raise KeyError("native lovelace provider is unavailable")
            return {
                "dashboard": await self._native_lovelace.create_dashboard(
                    title=arguments["title"],
                    url_path=arguments["url_path"],
                    user=user,
                    icon=arguments.get("icon"),
                    show_in_sidebar=arguments.get("show_in_sidebar", True),
                    require_admin=arguments.get("require_admin", False),
                    allow_single_word=arguments.get("allow_single_word", False),
                    config=arguments.get("config"),
                )
            }
        if tool_name == "hass.update_lovelace_dashboard_metadata":
            self._registry.validate_arguments(tool_name, arguments)
            if self._native_lovelace is None:
                raise KeyError("native lovelace provider is unavailable")
            return {
                "dashboard": await self._native_lovelace.update_dashboard_metadata(
                    arguments["url_path"],
                    user=user,
                    title=arguments.get("title"),
                    icon=arguments.get("icon"),
                    show_in_sidebar=arguments.get("show_in_sidebar"),
                    require_admin=arguments.get("require_admin"),
                )
            }
        if tool_name == "hass.save_lovelace_dashboard_config":
            self._registry.validate_arguments(tool_name, arguments)
            if self._native_lovelace is None:
                raise KeyError("native lovelace provider is unavailable")
            return {
                "dashboard": await self._native_lovelace.save_dashboard_config(
                    arguments["url_path"], arguments["config"], user=user
                )
            }
        if tool_name == "hass.delete_lovelace_dashboard":
            self._registry.validate_arguments(tool_name, arguments)
            if self._native_lovelace is None:
                raise KeyError("native lovelace provider is unavailable")
            return await self._native_lovelace.delete_dashboard(
                arguments["url_path"], user=user
            )
        if tool_name == "hass.list_lovelace_resources":
            self._registry.validate_arguments(tool_name, arguments)
            if self._lovelace_resources is None:
                raise KeyError("lovelace resource provider is unavailable")
            limit = arguments.get("limit", 100)
            return await self._lovelace_resources.list_resources(limit=limit)
        if tool_name == "hass.get_lovelace_resource":
            self._registry.validate_arguments(tool_name, arguments)
            if self._lovelace_resources is None:
                raise KeyError("lovelace resource provider is unavailable")
            return {
                "resource": await self._lovelace_resources.get_resource(
                    arguments["resource_id"]
                )
            }
        if tool_name.startswith("lovelace.") and self._managed is not None:
            return await self._managed.call(self._registry.call, tool_name, arguments)
        return self._registry.call(tool_name, arguments)

    def _jsonrpc_error(
        self, request_id: Any, code: int, message: str
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
