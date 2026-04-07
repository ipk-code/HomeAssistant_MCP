"""Tests for Home Assistant-facing HTTP integration helpers."""

# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from custom_components.homeassistant_mcp import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.homeassistant_mcp.const import (
    DOMAIN,
    INTEGRATION_VERSION,
    STORAGE_DIRECTORY,
    STREAMABLE_HTTP_API,
)
from custom_components.homeassistant_mcp.http import (
    KEY_HASS,
    HomeAssistantMCPStreamableView,
    async_register,
    get_runtime,
)


class _FakeConfig:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def path(self, value: str) -> str:
        return str(self._root / value)


class _FakeHTTP:
    def __init__(self) -> None:
        self.views = []

    def register_view(self, view) -> None:
        self.views.append(view)


class _FakeHass:
    def __init__(self, root: str) -> None:
        self.data = {}
        self.http = _FakeHTTP()
        self.config = _FakeConfig(root)
        self.executor_jobs = []

    async def async_add_executor_job(self, target, *args):
        self.executor_jobs.append((target, args))
        return target(*args)


class _FakeEntry:
    def __init__(self, entry_id: str) -> None:
        self.entry_id = entry_id


class _FakeRequest:
    def __init__(
        self, hass, *, body: dict | str, accept: str = "application/json"
    ) -> None:
        self.app = {KEY_HASS: hass}
        self.headers = {"accept": accept}
        self.content_type = "application/json"
        self._body = body

    async def text(self) -> str:
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)


def _response_json(response) -> dict:
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.text)


class HttpViewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.addAsyncCleanup(self._cleanup_tempdir)
        self.hass = _FakeHass(self.tempdir.name)
        self.entry = _FakeEntry("entry-1")

    async def _cleanup_tempdir(self) -> None:
        self.tempdir.cleanup()

    async def test_async_setup_registers_view_once(self) -> None:
        await async_setup(self.hass, {})
        await async_setup(self.hass, {})
        self.assertEqual(len(self.hass.http.views), 1)
        self.assertEqual(self.hass.http.views[0].url, STREAMABLE_HTTP_API)

    async def test_setup_entry_creates_runtime_in_storage_directory(self) -> None:
        await async_setup(self.hass, {})
        with self.assertLogs(
            "custom_components.homeassistant_mcp", level="INFO"
        ) as captured:
            await async_setup_entry(self.hass, self.entry)

        runtime = self.hass.data[DOMAIN][self.entry.entry_id]
        expected_root = (
            Path(self.tempdir.name) / STORAGE_DIRECTORY / self.entry.entry_id
        )
        self.assertEqual(runtime.root_path, expected_root)
        self.assertIsNotNone(runtime.discovery)
        self.assertEqual(len(self.hass.executor_jobs), 1)
        self.assertIs(get_runtime(self.hass), runtime)
        self.assertEqual(
            [item["uri"] for item in runtime.resources.list_payload()["resources"]],
            [
                "hass://config",
                "hass://entities",
                "hass://areas",
                "hass://devices",
                "hass://services",
                "hass://lovelace/dashboards",
            ],
        )
        self.assertEqual(
            runtime.resources.list_payload()["resourceTemplates"],
            [
                {
                    "uriTemplate": "hass://dashboard/{dashboard_id}",
                    "name": "Managed Dashboard",
                    "description": "A managed Lovelace dashboard document by dashboard identifier.",
                    "mimeType": "application/json",
                },
                {
                    "uriTemplate": "hass://lovelace/dashboard/{url_path}",
                    "name": "Native Lovelace Dashboard",
                    "description": "A native Home Assistant Lovelace dashboard document by url_path.",
                    "mimeType": "application/json",
                },
            ],
        )
        self.assertEqual(
            [item["name"] for item in runtime.prompts.list_prompts()],
            [
                "dashboard.builder",
                "dashboard.review",
                "dashboard.layout_consistency_review",
                "dashboard.entity_card_mapping",
                "dashboard.cleanup_audit",
            ],
        )
        self.assertEqual(
            await runtime.completions.async_complete(
                {"name": "dashboard.review"},
                {"name": "dashboard_id"},
            ),
            {"values": [], "hasMore": False},
        )
        self.assertEqual(
            runtime.completions.complete(
                {"name": "dashboard.review"},
                {"name": "icon", "value": "mdi:th"},
            )["values"],
            ["mdi:thermometer"],
        )
        self.assertTrue(
            any(
                f"Loaded Home Assistant MCP version {INTEGRATION_VERSION} entry" in line
                for line in captured.output
            )
        )

        with self.assertLogs(
            "custom_components.homeassistant_mcp", level="INFO"
        ) as unload_logs:
            await async_unload_entry(self.hass, self.entry)
        self.assertEqual(self.hass.data[DOMAIN], {})
        self.assertTrue(
            any(
                f"Unloaded Home Assistant MCP version {INTEGRATION_VERSION} entry"
                in line
                for line in unload_logs.output
            )
        )

    async def test_post_round_trip_to_transport(self) -> None:
        await async_setup(self.hass, {})
        await async_setup_entry(self.hass, self.entry)

        view = HomeAssistantMCPStreamableView()
        create_request = _FakeRequest(
            self.hass,
            body={
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
            },
        )
        create_response = await view.post(create_request)
        self.assertEqual(create_response.status, 200)

        list_request = _FakeRequest(
            self.hass,
            body={
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tools/call",
                "params": {"name": "lovelace.list_dashboards", "arguments": {}},
            },
        )
        list_response = await view.post(list_request)
        response_payload = _response_json(list_response)
        payload = json.loads(response_payload["result"]["content"][0]["text"])
        self.assertEqual(payload["dashboards"][0]["dashboard_id"], "main")

    async def test_post_without_runtime_returns_not_found(self) -> None:
        async_register(self.hass)
        view = HomeAssistantMCPStreamableView()
        response = await view.post(
            _FakeRequest(
                self.hass,
                body={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "tools/list",
                    "params": {},
                },
            )
        )
        self.assertEqual(response.status, 404)
        self.assertEqual(_response_json(response)["error"]["code"], -32004)
