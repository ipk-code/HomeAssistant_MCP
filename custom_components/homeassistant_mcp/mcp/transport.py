"""Stateless Streamable HTTP transport helpers for MCP requests."""

from __future__ import annotations

from http import HTTPStatus
import json
import logging
from typing import Any

from ..const import API_VERSION, MAX_REQUEST_BYTES, TITLE
from ..lovelace.errors import LovelaceMCPError
from .schema import ToolSchemaValidationError
from .server import ToolRegistry, load_api_contract

CONTENT_TYPE_JSON = "application/json"
_LOGGER = logging.getLogger(__name__)


class StatelessMCPTransport:
    """Minimal stateless MCP transport facade over the tool registry."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def handle_http_request(
        self, *, accept: str, content_type: str, body: str
    ) -> tuple[int, dict[str, Any] | None]:
        """Validate an HTTP request and dispatch a JSON-RPC message."""
        if CONTENT_TYPE_JSON not in accept:
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
            _LOGGER.warning("Rejected MCP request because body exceeded %s bytes", MAX_REQUEST_BYTES)
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
        return self.handle_jsonrpc_message(message)

    def handle_jsonrpc_message(
        self, message: dict[str, Any]
    ) -> tuple[int, dict[str, Any] | None]:
        """Handle a single JSON-RPC request in stateless mode."""
        if not isinstance(message, dict):
            _LOGGER.warning("Rejected MCP request because JSON-RPC payload was not an object")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                None, -32600, "JSON-RPC request must be an object"
            )
        if message.get("jsonrpc") != "2.0":
            _LOGGER.warning("Rejected MCP request because jsonrpc version was invalid")
            return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                message.get("id"), -32600, "jsonrpc must be '2.0'"
            )

        method = message.get("method")
        params = message.get("params") or {}

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
            _LOGGER.debug("Accepted MCP notification for method %s", method)
            return HTTPStatus.ACCEPTED, None

        if method == "initialize":
            _LOGGER.debug("Handled MCP initialize request %s", request_id)
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "1.0"),
                    "serverInfo": {"name": TITLE, "version": API_VERSION},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }

        if method == "ping":
            _LOGGER.debug("Handled MCP ping request %s", request_id)
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {},
            }

        if method == "tools/list":
            _LOGGER.debug("Handled MCP tools/list request %s", request_id)
            _, contracts = load_api_contract()
            return HTTPStatus.OK, {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": contract.name,
                            "description": contract.description,
                            "inputSchema": contract.input_schema,
                        }
                        for contract in contracts
                    ]
                },
            }

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                _LOGGER.warning("Rejected MCP tools/call request %s because name or arguments were invalid", request_id)
                return HTTPStatus.BAD_REQUEST, self._jsonrpc_error(
                    request_id, -32602, "tools/call requires name and arguments"
                )
            try:
                _LOGGER.debug("Executing MCP tool %s for request %s", tool_name, request_id)
                payload = self._registry.call(tool_name, arguments)
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(payload)}],
                        "isError": False,
                    },
                }
            except (KeyError, LovelaceMCPError, ToolSchemaValidationError) as err:
                _LOGGER.warning("MCP tool %s failed validation or execution for request %s: %s", tool_name, request_id, err)
                return HTTPStatus.OK, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": str(err)}],
                        "isError": True,
                    },
                }
            except Exception:
                _LOGGER.exception("Unexpected MCP transport failure for tool %s request %s", tool_name, request_id)
                return HTTPStatus.INTERNAL_SERVER_ERROR, self._jsonrpc_error(
                    request_id, -32603, "Internal server error"
                )

        _LOGGER.warning("Rejected MCP request %s because method %s is unknown", request_id, method)
        return HTTPStatus.NOT_FOUND, self._jsonrpc_error(
            request_id, -32601, f"Unknown method: {method}"
        )

    def _jsonrpc_error(
        self, request_id: Any, code: int, message: str
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
