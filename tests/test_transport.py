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
from custom_components.homeassistant_mcp.const import ADMIN_REQUIRED_TOOLS


class _FakeFrontendPanels:
    def list_panels(self, *, user=None, limit=200):
        is_admin = bool(getattr(user, "is_admin", False))
        panels = [
            {
                "component_name": "energy",
                "default_visible": True,
                "url_path": "energy",
                "require_admin": False,
                "source": "home_assistant_frontend",
                "panel_kind": "built_in",
            }
        ]
        if is_admin:
            panels.append(
                {
                    "component_name": "config",
                    "default_visible": True,
                    "url_path": "config",
                    "require_admin": True,
                    "source": "home_assistant_frontend",
                    "panel_kind": "built_in",
                }
            )
        return {"panels": panels[:limit], "truncated": False}

    def get_panel(self, url_path: str, *, user=None):
        if url_path == "energy":
            return {
                "component_name": "energy",
                "default_visible": True,
                "url_path": "energy",
                "require_admin": False,
                "source": "home_assistant_frontend",
                "panel_kind": "built_in",
            }
        if url_path == "config" and bool(getattr(user, "is_admin", False)):
            return {
                "component_name": "config",
                "default_visible": True,
                "url_path": "config",
                "require_admin": True,
                "source": "home_assistant_frontend",
                "panel_kind": "built_in",
            }
        raise KeyError(f"unknown frontend panel: {url_path}")


class _FakeLovelaceResources:
    async def list_resources(self, *, limit=200):
        return {
            "resource_mode": "storage",
            "resources": [
                {
                    "resource_id": "abc123",
                    "id_kind": "storage",
                    "resource_mode": "storage",
                    "type": "module",
                    "url": "/hacsfiles/frontend.js",
                    "source": "home_assistant_lovelace_resource",
                }
            ],
            "truncated": False,
        }

    async def get_resource(self, resource_id: str):
        if resource_id != "abc123":
            raise KeyError(f"unknown lovelace resource: {resource_id}")
        return {
            "resource_id": "abc123",
            "id_kind": "storage",
            "resource_mode": "storage",
            "type": "module",
            "url": "/hacsfiles/frontend.js",
            "source": "home_assistant_lovelace_resource",
        }


class _FakeTemplateSensors:
    async def list_sensors(self, *, user=None, limit=200):
        return {
            "sensors": [
                {
                    "config_entry_id": "0123456789abcdef0123456789abcdef",
                    "entity_id": "sensor.grid_import_power_total",
                    "name": "Grid Import Power Total",
                    "state": "{{ 1 }}",
                    "unit_of_measurement": "W",
                    "device_class": "power",
                    "state_class": "measurement",
                    "device_id": None,
                    "availability": None,
                    "source": "home_assistant_template_helper",
                }
            ],
            "truncated": False,
        }

    async def get_sensor(self, config_entry_id: str, *, user=None):
        if config_entry_id != "0123456789abcdef0123456789abcdef":
            raise KeyError(f"Unknown template sensor config entry: {config_entry_id}")
        return {
            "config_entry_id": config_entry_id,
            "entity_id": "sensor.grid_import_power_total",
            "name": "Grid Import Power Total",
            "state": "{{ 1 }}",
            "unit_of_measurement": "W",
            "device_class": "power",
            "state_class": "measurement",
            "device_id": None,
            "availability": None,
            "source": "home_assistant_template_helper",
        }

    async def preview_sensor(self, definition: dict, *, user=None):
        return {
            "state": "1",
            "attributes": {},
            "listeners": {"all": True},
            "error": None,
        }

    async def create_sensor(self, definition: dict, *, user=None):
        return await self.get_sensor("0123456789abcdef0123456789abcdef", user=user)

    async def update_sensor(self, config_entry_id: str, patch: dict, *, user=None):
        sensor = await self.get_sensor(config_entry_id, user=user)
        return sensor | patch

    async def delete_sensor(self, config_entry_id: str, *, user=None):
        return {
            "deleted": True,
            "sensor": await self.get_sensor(config_entry_id, user=user),
        }


class _FakeAdminUser:
    is_admin = True


class TransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.registry = ToolRegistry(YamlDashboardRepository(self.tempdir.name))
        self.resources = ResourceRegistry()
        self.prompts = PromptRegistry()
        self.completions = CompletionRegistry()
        self.resources.register(
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
        self.resources.register_template(
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
        self.prompts.register(
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
        self.completions.register(
            argument_name="dashboard_id",
            provider=lambda ref, argument: {
                "values": ["main"] if argument.get("value", "") in {"", "m"} else [],
                "hasMore": False,
            },
            ref_name="dashboard.review",
        )
        self.transport = StatelessMCPTransport(
            self.registry,
            resources=self.resources,
            prompts=self.prompts,
            completions=self.completions,
            lovelace_resources=_FakeLovelaceResources(),
            frontend_panels=_FakeFrontendPanels(),
            template_sensors=_FakeTemplateSensors(),
            admin_functions_enabled=False,
            admin_required_tools=ADMIN_REQUIRED_TOOLS,
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
        self.assertEqual(len(response["result"]["tools"]), 28)
        self.assertEqual(
            response["result"]["tools"][0]["name"], "lovelace.list_dashboards"
        )

    def test_admin_tools_are_hidden_and_rejected_when_disabled(self) -> None:
        listed = [tool["name"] for tool in self.transport.list_tools()]
        self.assertNotIn("hass.create_lovelace_dashboard", listed)

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "8",
                "method": "tools/call",
                "params": {
                    "name": "hass.create_lovelace_dashboard",
                    "arguments": {"title": "Temp", "url_path": "temp"},
                },
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        self.assertIn(
            "disabled by integration configuration",
            response["result"]["content"][0]["text"],
        )

    def test_admin_tools_can_be_listed_when_enabled(self) -> None:
        transport = StatelessMCPTransport(
            self.registry,
            resources=self.resources,
            prompts=self.prompts,
            completions=self.completions,
            lovelace_resources=_FakeLovelaceResources(),
            frontend_panels=_FakeFrontendPanels(),
            template_sensors=_FakeTemplateSensors(),
            admin_functions_enabled=True,
            admin_required_tools=ADMIN_REQUIRED_TOOLS,
        )
        listed = [tool["name"] for tool in transport.list_tools()]
        self.assertIn("hass.create_lovelace_dashboard", listed)
        self.assertIn("hass.create_template_sensor", listed)

    def test_async_template_sensor_tools_return_provider_payloads(self) -> None:
        async def _run() -> None:
            transport = StatelessMCPTransport(
                self.registry,
                resources=self.resources,
                prompts=self.prompts,
                completions=self.completions,
                lovelace_resources=_FakeLovelaceResources(),
                frontend_panels=_FakeFrontendPanels(),
                template_sensors=_FakeTemplateSensors(),
                admin_functions_enabled=True,
                admin_required_tools=ADMIN_REQUIRED_TOOLS,
            )
            status, response = await transport.handle_jsonrpc_message_async(
                {
                    "jsonrpc": "2.0",
                    "id": "8",
                    "method": "tools/call",
                    "params": {
                        "name": "hass.list_template_sensors",
                        "arguments": {},
                    },
                },
                user=_FakeAdminUser(),
            )
            self.assertEqual(status, 200)
            assert response is not None
            payload = json.loads(response["result"]["content"][0]["text"])
            self.assertEqual(
                payload["sensors"][0]["entity_id"], "sensor.grid_import_power_total"
            )

            status, response = await transport.handle_jsonrpc_message_async(
                {
                    "jsonrpc": "2.0",
                    "id": "9",
                    "method": "tools/call",
                    "params": {
                        "name": "hass.preview_template_sensor",
                        "arguments": {"name": "Grid Import", "state": "{{ 1 }}"},
                    },
                },
                user=_FakeAdminUser(),
            )
            self.assertEqual(status, 200)
            assert response is not None
            payload = json.loads(response["result"]["content"][0]["text"])
            self.assertEqual(payload["preview"]["state"], "1")

        import asyncio

        asyncio.run(_run())

    def test_async_lovelace_resource_tools_return_provider_payloads(self) -> None:
        async def _run() -> None:
            status, response = await self.transport.handle_jsonrpc_message_async(
                {
                    "jsonrpc": "2.0",
                    "id": "6",
                    "method": "tools/call",
                    "params": {
                        "name": "hass.list_lovelace_resources",
                        "arguments": {},
                    },
                }
            )
            self.assertEqual(status, 200)
            assert response is not None
            payload = json.loads(response["result"]["content"][0]["text"])
            self.assertEqual(payload["resources"][0]["resource_id"], "abc123")

            status, response = await self.transport.handle_jsonrpc_message_async(
                {
                    "jsonrpc": "2.0",
                    "id": "7",
                    "method": "tools/call",
                    "params": {
                        "name": "hass.get_lovelace_resource",
                        "arguments": {"resource_id": "abc123"},
                    },
                }
            )
            self.assertEqual(status, 200)
            assert response is not None
            payload = json.loads(response["result"]["content"][0]["text"])
            self.assertEqual(payload["resource"]["type"], "module")

        import asyncio

        asyncio.run(_run())

    def test_frontend_panel_tools_respect_user_visibility(self) -> None:
        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "4",
                "method": "tools/call",
                "params": {
                    "name": "hass.list_frontend_panels",
                    "arguments": {},
                },
            }
        )
        self.assertEqual(status, 200)
        assert response is not None
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual([item["url_path"] for item in payload["panels"]], ["energy"])

        status, response = self.transport.handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": "5",
                "method": "tools/call",
                "params": {
                    "name": "hass.get_frontend_panel",
                    "arguments": {"url_path": "config"},
                },
            },
            user=_FakeAdminUser(),
        )
        self.assertEqual(status, 200)
        assert response is not None
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["panel"]["url_path"], "config")

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

    def test_log_injection_via_method_name_is_neutralised(self) -> None:
        """CWE-117: Newlines in user-supplied method names must not reach the log."""
        import logging

        with self.assertLogs(
            "custom_components.homeassistant_mcp.mcp.transport", level=logging.WARNING
        ) as captured:
            status, _resp = self.transport.handle_jsonrpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "unknown\nINJECTED fake log line",
                    "params": {},
                }
            )
        self.assertEqual(status, 404)
        for line in captured.output:
            self.assertNotIn("\n", line, "Raw newline leaked into log output")
            self.assertIn("\\x0a", line, "Newline should appear hex-escaped in log")

    def test_log_injection_via_request_id_is_neutralised(self) -> None:
        """CWE-117: Newlines in request_id must not reach the log."""
        import logging

        with self.assertLogs(
            "custom_components.homeassistant_mcp.mcp.transport", level=logging.DEBUG
        ) as captured:
            status, _resp = self.transport.handle_jsonrpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": "abc\nINJECTED",
                    "method": "ping",
                    "params": {},
                }
            )
        self.assertEqual(status, 200)
        for line in captured.output:
            self.assertNotIn("\n", line, "Raw newline leaked into log output")

    def test_accept_header_substring_false_positive_is_rejected(self) -> None:
        """Accept: application/json-patch+json must NOT satisfy the json check."""
        status, response = self.transport.handle_http_request(
            accept="application/json-patch+json",
            content_type="application/json",
            body='{"jsonrpc":"2.0","id":"1","method":"ping","params":{}}',
        )
        self.assertEqual(status, 400)

    def test_accept_wildcard_is_accepted(self) -> None:
        """Accept: */* must be treated as accepting application/json."""
        status, response = self.transport.handle_http_request(
            accept="*/*",
            content_type="application/json",
            body='{"jsonrpc":"2.0","id":"1","method":"ping","params":{}}',
        )
        self.assertEqual(status, 200)

    def test_accept_application_wildcard_is_accepted(self) -> None:
        """Accept: application/* must be treated as accepting application/json."""
        status, response = self.transport.handle_http_request(
            accept="application/*",
            content_type="application/json",
            body='{"jsonrpc":"2.0","id":"1","method":"ping","params":{}}',
        )
        self.assertEqual(status, 200)

    def test_log_sanitizer_strips_null_bytes_and_ansi_escapes(self) -> None:
        """CWE-117: Null bytes and ANSI escape sequences must not pass through _s()."""
        from custom_components.homeassistant_mcp.mcp.transport import _s

        # Null byte — can truncate log entries in some log aggregators
        self.assertNotIn("\x00", _s("before\x00after"))
        self.assertIn("\\x00", _s("before\x00after"))

        # ANSI escape sequence — can corrupt terminal output and hide log lines
        ansi_input = "normal\x1b[31mred\x1b[0mnormal"
        sanitized = _s(ansi_input)
        self.assertNotIn("\x1b", sanitized)
        self.assertIn("\\x1b", sanitized)

        # Tab and other control characters
        self.assertNotIn("\t", _s("a\tb"))
        self.assertIn("\\x09", _s("a\tb"))

        # Printable ASCII and non-ASCII (unicode) pass through unchanged
        self.assertEqual(_s("hello world"), "hello world")
        self.assertEqual(_s("café"), "café")

    def test_tool_result_rejects_nan_in_json_serialization(self) -> None:
        """CWE-20: Tool results containing NaN must not produce invalid JSON."""
        # Register a tool that returns NaN in its result. The transport must
        # catch this at the json.dumps boundary rather than emitting a
        # non-standard NaN token that breaks strict JSON parsers.
        import types

        original_call = self.transport._registry.call

        def patched_call(name, arguments):
            if name == "lovelace.list_dashboards":
                return {"dashboards": [], "bad": float("nan")}
            return original_call(name, arguments)

        self.transport._registry.call = patched_call
        try:
            status, response = self.transport.handle_jsonrpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "tools/call",
                    "params": {"name": "lovelace.list_dashboards", "arguments": {}},
                }
            )
            # Must either return a structured error or an HTTP 500, but never
            # produce a response body containing the NaN token.
            if status == 200 and response is not None:
                result = response.get("result", {})
                if not result.get("isError"):
                    self.fail("NaN in tool result should not produce a success response")
        finally:
            self.transport._registry.call = original_call
