"""Read-only access to Home Assistant frontend panels."""

from __future__ import annotations

from typing import Any


_REDACTED = "[redacted]"
_SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token",
}
_MAX_CONFIG_DEPTH = 8


class FrontendPanelProvider:
    """Expose Home Assistant frontend panels without mutating them."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    def list_panels(
        self, *, user: Any | None = None, limit: int = 200
    ) -> dict[str, Any]:
        """List frontend panels visible to the authenticated user."""
        panels = []
        for url_path, panel in sorted(self._panels().items(), key=self._sort_key):
            serialized = self._serialize_panel(url_path, panel, user=user)
            if serialized is None:
                continue
            panels.append(serialized)
        truncated = len(panels) > limit
        return {"panels": panels[:limit], "truncated": truncated}

    def get_panel(self, url_path: str, *, user: Any | None = None) -> dict[str, Any]:
        """Return one frontend panel visible to the authenticated user."""
        panel = self._panels().get(url_path)
        if panel is None:
            raise KeyError(f"unknown frontend panel: {url_path}")
        serialized = self._serialize_panel(url_path, panel, user=user)
        if serialized is None:
            raise KeyError(f"unknown frontend panel: {url_path}")
        return serialized

    def _panels(self) -> dict[str, Any]:
        from homeassistant.components.frontend import DATA_PANELS

        return self._hass.data.get(DATA_PANELS, {})

    def _serialize_panel(
        self, url_path: str, panel: Any, *, user: Any | None = None
    ) -> dict[str, Any] | None:
        if bool(getattr(panel, "require_admin", False)) and not self._user_is_admin(
            user
        ):
            return None

        if callable(getattr(panel, "to_response", None)):
            payload = dict(panel.to_response())
        else:
            payload = {
                "component_name": getattr(panel, "component_name", None),
                "icon": getattr(panel, "sidebar_icon", None),
                "title": getattr(panel, "sidebar_title", None),
                "default_visible": bool(
                    getattr(panel, "sidebar_default_visible", True)
                ),
                "config": getattr(panel, "config", None),
                "url_path": getattr(panel, "frontend_url_path", url_path),
                "require_admin": bool(getattr(panel, "require_admin", False)),
                "config_panel_domain": getattr(panel, "config_panel_domain", None),
            }

        payload["url_path"] = str(payload.get("url_path") or url_path)
        payload["source"] = "home_assistant_frontend"
        payload["panel_kind"] = self._panel_kind(payload)
        payload["config"] = self._sanitize_value(payload.get("config"), depth=0)
        return payload

    def _panel_kind(self, payload: dict[str, Any]) -> str:
        component_name = payload.get("component_name")
        config = payload.get("config")
        if component_name == "lovelace":
            return "lovelace"
        if isinstance(config, dict) and "_panel_custom" in config:
            return "custom_panel"
        if component_name == "custom":
            return "custom_panel"
        return "built_in"

    def _sanitize_value(self, value: Any, *, depth: int) -> Any:
        if depth >= _MAX_CONFIG_DEPTH:
            return "[truncated]"
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, nested in value.items():
                key_text = str(key)
                if self._is_sensitive_key(key_text):
                    sanitized[key_text] = _REDACTED
                    continue
                sanitized[key_text] = self._sanitize_value(nested, depth=depth + 1)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize_value(item, depth=depth + 1) for item in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    def _is_sensitive_key(self, key: str) -> bool:
        normalized = key.casefold().replace("-", "_")
        return normalized in _SENSITIVE_KEYS or normalized.endswith("_token")

    def _sort_key(self, item: tuple[str, Any]) -> tuple[str, str]:
        url_path, panel = item
        title = getattr(panel, "sidebar_title", None)
        if callable(getattr(panel, "to_response", None)):
            title = panel.to_response().get("title")
        return (str(title or "").casefold(), url_path)

    def _user_is_admin(self, user: Any | None) -> bool:
        return bool(getattr(user, "is_admin", False))
