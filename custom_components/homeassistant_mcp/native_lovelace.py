"""Read-only access to native Home Assistant Lovelace dashboards."""

from __future__ import annotations

from typing import Any


class NativeLovelaceProvider:
    """Expose native Home Assistant Lovelace dashboards without mutating them."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    async def list_dashboards(self, *, limit: int = 200) -> dict[str, Any]:
        """List native Home Assistant Lovelace dashboards."""
        dashboards = []
        for key, config in sorted(
            self._dashboards().items(),
            key=lambda item: self._sort_key(item[0], item[1]),
        ):
            dashboards.append(await self._summary_for_dashboard(key, config))
        truncated = len(dashboards) > limit
        return {"dashboards": dashboards[:limit], "truncated": truncated}

    async def get_dashboard(self, url_path: str) -> dict[str, Any]:
        """Return one native Home Assistant Lovelace dashboard."""
        key, config = self._resolve_dashboard(url_path)
        summary = await self._summary_for_dashboard(key, config)
        try:
            payload = await config.async_load(False)
        except Exception as err:  # pragma: no cover - HA runtime specific
            raise KeyError(f"unknown lovelace dashboard: {url_path}") from err
        return {"metadata": summary, "config": payload}

    def _dashboards(self) -> dict[str | None, Any]:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = self._hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            return {}
        return lovelace_data.dashboards

    def _resolve_dashboard(self, url_path: str) -> tuple[str | None, Any]:
        from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN

        dashboards = self._dashboards()
        if url_path == "default":
            config = dashboards.get(LOVELACE_DOMAIN) or dashboards.get(None)
            if config is None:
                raise KeyError(f"unknown lovelace dashboard: {url_path}")
            key = (
                LOVELACE_DOMAIN if dashboards.get(LOVELACE_DOMAIN) is not None else None
            )
            return key, config

        config = dashboards.get(url_path)
        if config is None:
            raise KeyError(f"unknown lovelace dashboard: {url_path}")
        return url_path, config

    async def _summary_for_dashboard(
        self, key: str | None, config: Any
    ) -> dict[str, Any]:
        metadata = config.config or {}
        info = await config.async_get_info()
        url_path = self._resource_url_path(key, config)
        summary = {
            "id": metadata.get("id")
            or ("default" if url_path == "default" else url_path),
            "title": metadata.get("title")
            or ("Default" if url_path == "default" else url_path),
            "url_path": url_path,
            "mode": info.get("mode", getattr(config, "mode", "unknown")),
            "source": "home_assistant_lovelace",
            "view_count": info.get("views", 0),
        }
        if "show_in_sidebar" in metadata:
            summary["show_in_sidebar"] = metadata["show_in_sidebar"]
        if "require_admin" in metadata:
            summary["require_admin"] = metadata["require_admin"]
        if "icon" in metadata:
            summary["icon"] = metadata["icon"]
        return summary

    def _resource_url_path(self, key: str | None, config: Any) -> str:
        from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN

        if key in {None, LOVELACE_DOMAIN} and config.url_path is None:
            return "default"
        if config.url_path is not None:
            return config.url_path
        return "default"

    def _sort_key(self, key: str | None, config: Any) -> tuple[str, str]:
        metadata = config.config or {}
        title = str(metadata.get("title") or "").casefold()
        return (title, self._resource_url_path(key, config))
