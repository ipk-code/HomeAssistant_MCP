"""Tests for the stateless MCP transport."""

from __future__ import annotations

import json
from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp.lovelace.repository import (
    YamlDashboardRepository,
)
from custom_components.homeassistant_mcp.mcp.completions import CompletionRegistry
from custom_components.homeassistant_mcp.mcp.prompts import (
    PromptArgument,
    PromptDefinition,
    PromptRegistry,
)
from custom_components.homeassistant_mcp.mcp.resources import (
    ResourceDefinition,
    ResourceRegistry,
    ResourceTemplateDefinition,
)
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
        resources = ResourceRegistry()
        prompts = PromptRegistry()
        completions = CompletionRegistry()
        resources.register(
            ResourceDefinition(
                uri="hass://test",
                name="Test Resource",
                description="Fixture resource",
                mime_type="application/json",
            ),
            lambda: [
                {"uri": "hass://test", "mimeType": "application/json", "text": "{}"}
            ],
        )
        resources.register_template(
            ResourceTemplateDefinition(
                uri_template="hass://dashboard/{dashboard_id}",
                name="Dashboard",
                description="Dashboard template",
                mime_type="application/json",
            ),
            lambda params, uri: [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": params["dashboard_id"],
                }
            ],
        )
        prompts.register(
            PromptDefinition(
                name="dashboard.review",
                description="Review one dashboard",
                arguments=(
                    PromptArgument(
                        name="dashboard_id",
                        description="Dashboard identifier",
                        required=True,
                    ),
                ),
            ),
            lambda arguments: {
                "description": "Dashboard review",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Review {arguments['dashboard_id']}",
                        },
                    }
                ],
            },
        )
        completions.register(
            argument_name="dashboard_id",
            provider=lambda ref, argument: {
                "values": ["main"] if argument.get("value", "") in {"", "m"} else [],
                "hasMore": False,
            },
            ref_name="dashboard.review",
        )
        self.transport = StatelessMCPTransport(
            registry,
            resources=resources,
            prompts=prompts,
            completions=completions,
        )

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
        self.assertIn("resources", response["result"]["capabilities"])
        self.assertIn("prompts", response["result"]["capabilities"])

    def test_tools_list_returns_contracts(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(len(response["result"]["tools"]), 24)
        self.assertEqual(
            response["result"]["tools"][0]["name"], "lovelace.list_dashboards"
        )

    def test_resources_list_and_read_use_registry(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": "1", "method": "resources/list", "params": {}}
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(response["result"]["resources"][0]["uri"], "hass://test")
        self.assertEqual(
            response["result"]["resourceTemplates"][0]["uriTemplate"],
            "hass://dashboard/{dashboard_id}",
        )

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "resources/read",
                "params": {"uri": "hass://test"},
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(response["result"]["contents"][0]["uri"], "hass://test")

    def test_resources_read_supports_template_backed_resources(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "3",
                "method": "resources/read",
                "params": {"uri": "hass://dashboard/main"},
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(response["result"]["contents"][0]["text"], "main")

    def test_resources_read_unknown_uri_is_rejected(self) -> None:
        with self.assertNoLogs(
            "custom_components.homeassistant_mcp.mcp.transport", level="WARNING"
        ):
            status, response = self.transport.handle_jsonrpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "resources/read",
                    "params": {"uri": "hass://missing"},
                }
            )
        self.assertEqual(status, 400)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_prompts_list_and_get_use_registry(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": "1", "method": "prompts/list", "params": {}}
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(response["result"]["prompts"][0]["name"], "dashboard.review")

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "prompts/get",
                "params": {
                    "name": "dashboard.review",
                    "arguments": {"dashboard_id": "main"},
                },
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(
            response["result"]["messages"][0]["content"]["text"], "Review main"
        )

    def test_prompt_lookup_and_completion_validation(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "prompts/get",
                "params": {"name": "dashboard.missing", "arguments": {}},
            }
        )
        self.assertEqual(status, 400)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "completion/complete",
                "params": {
                    "ref": {"name": "dashboard.review"},
                    "argument": {"name": "dashboard_id", "value": "m"},
                },
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(response["result"]["completion"]["values"], ["main"])

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "3",
                "method": "completion/complete",
                "params": {"ref": [], "argument": {}},
            }
        )
        self.assertEqual(status, 400)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_completion_transport_limits_provider_output(self) -> None:
        completions = CompletionRegistry()
        completions.register(
            argument_name="entity_id",
            provider=lambda ref, argument: {
                "values": [f"sensor.item_{index}" for index in range(40)],
                "hasMore": False,
            },
        )
        transport = StatelessMCPTransport(
            self.transport._registry, completions=completions
        )

        status, response = transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "4",
                "method": "completion/complete",
                "params": {
                    "ref": {"name": "dashboard.review"},
                    "argument": {"name": "entity_id", "value": "sensor."},
                },
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertEqual(len(response["result"]["completion"]["values"]), 25)
        self.assertTrue(response["result"]["completion"]["hasMore"])

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

    def test_non_object_params_are_rejected_before_method_dispatch(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": []}
        )
        self.assertEqual(status, 400)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_http_validation_rejects_bad_headers_and_bad_json(self) -> None:
        with self.assertLogs(
            "custom_components.homeassistant_mcp.mcp.transport", level="WARNING"
        ) as captured:
            status, response = self.transport.handle_http_request(
                accept="text/plain", content_type=CONTENT_TYPE_JSON, body="{}"
            )
        self.assertEqual(status, 400)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32600)
        self.assertIn("Accept header is invalid", captured.output[0])

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
        with self.assertLogs(
            "custom_components.homeassistant_mcp.mcp.transport", level="WARNING"
        ) as captured:
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
        self.assertIn("MCP tool lovelace.nope failed", captured.output[0])

    def test_invalid_tool_arguments_are_rejected_before_dispatch(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {
                    "name": "lovelace.create_dashboard",
                    "arguments": {"dashboard_id": "main", "url_path": "main"},
                },
            }
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        self.assertIn("required", response["result"]["content"][0]["text"])
