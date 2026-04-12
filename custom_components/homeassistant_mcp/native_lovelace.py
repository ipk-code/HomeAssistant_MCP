"""Read-only access to native Home Assistant Lovelace dashboards."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from .lovelace.errors import (
    DashboardNotFoundError,
    DashboardPermissionError,
    DashboardValidationError,
    UnsupportedDashboardOperationError,
)


class NativeLovelaceProvider:
    """Expose native Home Assistant Lovelace dashboards and storage writes."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    async def list_dashboards(
        self, *, user: Any | None = None, limit: int = 200
    ) -> dict[str, Any]:
        """List native Home Assistant Lovelace dashboards."""
        dashboards = []
        for key, config in sorted(
            self._dashboards().items(),
            key=lambda item: self._sort_key(item[0], item[1]),
        ):
            summary = await self._summary_for_dashboard(key, config)
            if summary is None:
                continue
            dashboards.append(summary)
        truncated = len(dashboards) > limit
        return {"dashboards": dashboards[:limit], "truncated": truncated}

    async def get_dashboard(
        self, url_path: str, *, user: Any | None = None
    ) -> dict[str, Any]:
        """Return one native Home Assistant Lovelace dashboard."""
        key, config = self._resolve_dashboard(url_path)
        summary = await self._summary_for_dashboard(key, config, user=user)
        if summary is None:
            raise KeyError(f"unknown lovelace dashboard: {url_path}")
        try:
            payload = await config.async_load(False)
        except Exception as err:  # pragma: no cover - HA runtime specific
            raise KeyError(f"unknown lovelace dashboard: {url_path}") from err
        return {"metadata": summary, "config": payload}

    async def create_dashboard(
        self,
        *,
        title: str,
        url_path: str,
        user: Any | None = None,
        icon: str | None = None,
        show_in_sidebar: bool = True,
        require_admin: bool = False,
        allow_single_word: bool = False,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a storage-based Home Assistant Lovelace dashboard."""
        self._require_admin(user)

        from homeassistant.components.lovelace import dashboard as lovelace_dashboard
        from homeassistant.components.lovelace.const import (
            CONF_ALLOW_SINGLE_WORD,
            CONF_ICON,
            CONF_REQUIRE_ADMIN,
            CONF_SHOW_IN_SIDEBAR,
            CONF_TITLE,
            CONF_URL_PATH,
            MODE_STORAGE,
        )
        from homeassistant.components.lovelace import _register_panel

        collection = await self._load_dashboards_collection()
        create_data: dict[str, Any] = {
            CONF_TITLE: title,
            CONF_URL_PATH: url_path,
            CONF_SHOW_IN_SIDEBAR: show_in_sidebar,
            CONF_REQUIRE_ADMIN: require_admin,
            CONF_ALLOW_SINGLE_WORD: allow_single_word,
            "mode": MODE_STORAGE,
        }
        if icon is not None:
            create_data[CONF_ICON] = icon

        try:
            item = await collection.async_create_item(create_data)
        except (HomeAssistantError, ValueError, vol.Invalid) as err:
            raise DashboardValidationError(str(err)) from err

        await self._persist_collection(collection)

        store = lovelace_dashboard.LovelaceStorage(self._hass, item)
        self._lovelace_data().dashboards[url_path] = store
        _register_panel(self._hass, url_path, MODE_STORAGE, item, False)
        try:
            await store.async_save(config or {"views": []})
        except HomeAssistantError as err:
            raise DashboardValidationError(str(err)) from err
        return await self.get_dashboard(url_path, user=user)

    async def update_dashboard_metadata(
        self,
        url_path: str,
        *,
        user: Any | None = None,
        title: str | None = None,
        icon: str | None = None,
        show_in_sidebar: bool | None = None,
        require_admin: bool | None = None,
    ) -> dict[str, Any]:
        """Update metadata for one storage dashboard."""
        self._require_admin(user)

        from homeassistant.components.lovelace import _register_panel
        from homeassistant.components.lovelace.const import MODE_STORAGE

        _key, config = self._resolve_dashboard(url_path)
        self._require_mutable_storage_dashboard(url_path, config)
        collection = await self._load_dashboards_collection()
        item_id = self._find_dashboard_item_id(collection, url_path)
        update_data = {
            key: value
            for key, value in {
                "title": title,
                "icon": icon,
                "show_in_sidebar": show_in_sidebar,
                "require_admin": require_admin,
            }.items()
            if value is not None
        }
        try:
            item = await collection.async_update_item(item_id, update_data)
        except (HomeAssistantError, ValueError, vol.Invalid) as err:
            raise DashboardValidationError(str(err)) from err

        await self._persist_collection(collection)
        config.config = item
        _register_panel(self._hass, url_path, MODE_STORAGE, item, True)
        return await self.get_dashboard(url_path, user=user)

    async def save_dashboard_config(
        self, url_path: str, config: dict[str, Any], *, user: Any | None = None
    ) -> dict[str, Any]:
        """Replace the config for one storage dashboard."""
        self._require_admin(user)

        _key, dashboard = self._resolve_dashboard(url_path)
        self._require_mutable_storage_dashboard(url_path, dashboard)
        try:
            await dashboard.async_save(config)
        except HomeAssistantError as err:
            raise DashboardValidationError(str(err)) from err
        return await self.get_dashboard(url_path, user=user)

    async def delete_dashboard(
        self, url_path: str, *, user: Any | None = None
    ) -> dict[str, Any]:
        """Delete one storage dashboard."""
        self._require_admin(user)

        from homeassistant.components import frontend

        _key, dashboard = self._resolve_dashboard(url_path)
        self._require_mutable_storage_dashboard(url_path, dashboard)
        summary = await self._summary_for_dashboard(url_path, dashboard, user=user)
        if summary is None:
            raise DashboardNotFoundError(f"unknown lovelace dashboard: {url_path}")

        collection = await self._load_dashboards_collection()
        item_id = self._find_dashboard_item_id(collection, url_path)
        try:
            await collection.async_delete_item(item_id)
        except HomeAssistantError as err:
            raise DashboardValidationError(str(err)) from err
        await self._persist_collection(collection)

        frontend.async_remove_panel(self._hass, url_path)
        try:
            await dashboard.async_delete()
        except HomeAssistantError as err:
            raise DashboardValidationError(str(err)) from err
        self._lovelace_data().dashboards.pop(url_path, None)
        return {"deleted": True, "dashboard": summary}

    def _dashboards(self) -> dict[str | None, Any]:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = self._hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            return {}
        return lovelace_data.dashboards

    def _lovelace_data(self) -> Any:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = self._hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            raise DashboardNotFoundError("Home Assistant Lovelace is unavailable")
        return lovelace_data

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
        self, key: str | None, config: Any, *, user: Any | None = None
    ) -> dict[str, Any] | None:
        metadata = config.config or {}
        if bool(metadata.get("require_admin")) and not self._user_is_admin(user):
            return None
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

    async def _load_dashboards_collection(self) -> Any:
        from homeassistant.components.lovelace.dashboard import DashboardsCollection

        collection = DashboardsCollection(self._hass)
        await collection.async_load()
        return collection

    async def _persist_collection(self, collection: Any) -> None:
        try:
            await collection.store.async_save(collection._data_to_save())
        except HomeAssistantError as err:
            raise DashboardValidationError(str(err)) from err

    def _find_dashboard_item_id(self, collection: Any, url_path: str) -> str:
        for item in collection.async_items():
            if item.get("url_path") == url_path:
                return item["id"]
        raise DashboardNotFoundError(f"unknown lovelace dashboard: {url_path}")

    def _require_admin(self, user: Any | None) -> None:
        if self._user_is_admin(user):
            return
        raise DashboardPermissionError(
            "native lovelace dashboard writes require a Home Assistant admin user"
        )

    def _require_mutable_storage_dashboard(self, url_path: str, config: Any) -> None:
        from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
        from homeassistant.components.lovelace.const import MODE_STORAGE

        if url_path in {"default", LOVELACE_DOMAIN} or config.url_path is None:
            raise UnsupportedDashboardOperationError(
                "the default Home Assistant Lovelace dashboard is not writable through MCP"
            )
        if getattr(config, "mode", None) != MODE_STORAGE:
            raise UnsupportedDashboardOperationError(
                "only storage-mode Home Assistant Lovelace dashboards are writable through MCP"
            )
        info = getattr(config, "config", {}) or {}
        if info.get("mode") == "auto-gen":
            raise UnsupportedDashboardOperationError(
                "auto-generated Home Assistant dashboards are not writable through MCP"
            )

    def _user_is_admin(self, user: Any | None) -> bool:
        return bool(getattr(user, "is_admin", False))
