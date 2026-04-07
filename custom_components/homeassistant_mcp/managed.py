"""Async helpers for managed MCP dashboard repository access."""

from __future__ import annotations

from typing import Any, Callable

from .lovelace.repository import YamlDashboardRepository


class ManagedDashboardExecutor:
    """Run blocking repository operations through Home Assistant's executor."""

    def __init__(self, hass: Any, repository: YamlDashboardRepository) -> None:
        self._hass = hass
        self._repository = repository

    async def call(self, func: Callable[..., Any], *args: Any) -> Any:
        """Execute a blocking repository function in the executor."""
        return await self._hass.async_add_executor_job(func, *args)

    async def list_dashboards(self) -> list[dict[str, Any]]:
        return await self.call(self._repository.list_dashboards)

    async def get_dashboard(self, dashboard_id: str) -> dict[str, Any]:
        return await self.call(self._repository.get_dashboard, dashboard_id)

    async def list_views(self, dashboard_id: str) -> list[dict[str, Any]]:
        return await self.call(self._repository.list_views, dashboard_id)

    async def list_cards(self, dashboard_id: str, view_id: str) -> list[dict[str, Any]]:
        return await self.call(self._repository.list_cards, dashboard_id, view_id)
