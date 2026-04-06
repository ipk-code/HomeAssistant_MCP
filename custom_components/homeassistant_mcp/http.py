"""HTTP view wiring for the stateless MCP transport."""

# pyright: reportMissingImports=false, reportGeneralTypeIssues=false, reportUntypedBaseClass=false

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

try:
    from aiohttp import web
    from homeassistant.components.http import KEY_HASS, HomeAssistantView
except ModuleNotFoundError:  # pragma: no cover - exercised in unit tests only
    KEY_HASS = "hass"

    @dataclass
    class _FallbackResponse:
        status: int
        data: Any

        async def text(self) -> str:
            return str(self.data)

    class _FallbackWeb:
        @staticmethod
        def json_response(*, data: Any, status: int = HTTPStatus.OK) -> _FallbackResponse:
            return _FallbackResponse(status=status, data=data)

        @staticmethod
        def Response(*, status: int = HTTPStatus.OK, text: str = "") -> _FallbackResponse:
            return _FallbackResponse(status=status, data=text)

    web = _FallbackWeb()  # type: ignore[assignment]

    class HomeAssistantView:  # type: ignore[override]
        name = ""
        url = ""
        requires_auth = True

from .const import DOMAIN, STREAMABLE_HTTP_API
from .runtime import IntegrationRuntime


def async_register(hass: Any) -> None:
    """Register the stateless MCP HTTP view once."""
    if hass.data.get(f"{DOMAIN}_http_registered"):
        return
    hass.http.register_view(HomeAssistantMCPStreamableView())
    hass.data[f"{DOMAIN}_http_registered"] = True


def get_runtime(hass: Any) -> IntegrationRuntime:
    """Get the active runtime.

    The integration currently allows only one config entry, so request handling
    always targets the single loaded runtime.
    """
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if not runtimes:
        raise RuntimeError("Home Assistant MCP is not configured")
    if len(runtimes) > 1:
        raise RuntimeError("Home Assistant MCP found multiple runtimes")
    return runtimes[0]


class HomeAssistantMCPStreamableView(HomeAssistantView):
    """Home Assistant view for stateless Streamable HTTP MCP requests."""

    name = f"{DOMAIN}:streamable"
    url = STREAMABLE_HTTP_API
    requires_auth = True

    async def get(self, request: Any) -> Any:
        return web.Response(
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            text="Only POST method is supported",
        )

    async def post(self, request: Any) -> Any:
        hass = request.app[KEY_HASS]
        try:
            runtime = get_runtime(hass)
        except RuntimeError as err:
            return web.json_response(
                status=HTTPStatus.NOT_FOUND,
                data={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32004, "message": str(err)},
                },
            )

        status, payload = runtime.transport.handle_http_request(
            accept=request.headers.get("accept", ""),
            content_type=request.content_type,
            body=await request.text(),
        )
        if payload is None:
            return web.Response(status=status)
        return web.json_response(status=status, data=payload)
