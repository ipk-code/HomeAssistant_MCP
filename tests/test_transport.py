"""Tests for the stateless MCP transport."""

from __future__ import annotations

import json
from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp.lovelace.repository import YamlDashboardRepository
from custom_components.homeassistant_mcp.mcp.server import ToolRegistry
from custom_components.homeassistant_mcp.mcp.transport import (
    CONTENT_TYPE_JSON,
    StatelessMCPTransport,
)


class TransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        registry = ToolRegistry(YamlDashboardRepository(self.tempdir.name))
        self.transport = StatelessMCPTransport(registry)

    def test_initialize_request(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "initialize",
                "params": {"protocolVersion": "1.0", "clientInfo": {"name": "test"}},
            }
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["result"]["serverInfo"]["name"], "Home Assistant MCP")
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list_returns_contracts(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(len(response["result"]["tools"]), 17)
        self.assertEqual(response["result"]["tools"][0]["name"], "lovelace.list_dashboards")

    def test_tools_call_round_trip(self) -> None:
        create_status, create_response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {
                    "name": "lovelace.create_dashboard",
                    "arguments": {
                        "dashboard_id": "main",
                        "title": "Main",
                        "url_path": "main",
                        "views": [],
                    },
                },
            }
        )
        self.assertEqual(create_status, 200)
        self.assertIsNotNone(create_response)
        assert create_response is not None
        self.assertFalse(create_response["result"]["isError"])

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tools/call",
                "params": {
                    "name": "lovelace.list_dashboards",
                    "arguments": {},
                },
            }
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(response)
        assert response is not None
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["dashboards"][0]["dashboard_id"], "main")

    def test_notifications_return_accepted_without_body(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {"jsonrpc": "2.0", "method": "ping", "params": {}}
        )
        self.assertEqual(status, 202)
        self.assertIsNone(response)

    def test_malformed_notification_is_rejected(self) -> None:
        status, response = self.transport.handle_jsonrpc_message({"jsonrpc": "2.0"})
        self.assertEqual(status, 400)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32600)

    def test_http_validation_rejects_bad_headers_and_bad_json(self) -> None:
        status, response = self.transport.handle_http_request(
            accept="text/plain", content_type=CONTENT_TYPE_JSON, body="{}"
        )
        self.assertEqual(status, 400)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32600)

        status, response = self.transport.handle_http_request(
            accept=CONTENT_TYPE_JSON, content_type=CONTENT_TYPE_JSON, body="{"
        )
        self.assertEqual(status, 400)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32700)

    def test_http_validation_rejects_oversized_body(self) -> None:
        status, response = self.transport.handle_http_request(
            accept=CONTENT_TYPE_JSON,
            content_type=CONTENT_TYPE_JSON,
            body="x" * (1048576 + 1),
        )
        self.assertEqual(status, 413)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32013)

    def test_unknown_tool_returns_tool_error_result(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {"name": "lovelace.nope", "arguments": {}},
            }
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
