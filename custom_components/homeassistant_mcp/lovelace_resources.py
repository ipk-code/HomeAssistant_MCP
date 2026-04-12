"""Read-only access to Home Assistant Lovelace resources."""

from __future__ import annotations

from hashlib import sha1
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_REDACTED = "[redacted]"
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token",
}


class LovelaceResourceProvider:
    """Expose Lovelace resources without mutating them."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    async def list_resources(self, *, limit: int = 200) -> dict[str, Any]:
        """List configured Lovelace resources."""
        resources = await self._serialized_resources()
        truncated = len(resources) > limit
        return {
            "resource_mode": self._resource_mode(),
            "resources": resources[:limit],
            "truncated": truncated,
        }

    async def get_resource(self, resource_id: str) -> dict[str, Any]:
        """Return one Lovelace resource by resource identifier."""
        for resource in await self._serialized_resources():
            if resource["resource_id"] == resource_id:
                return resource
        raise KeyError(f"unknown lovelace resource: {resource_id}")

    async def _serialized_resources(self) -> list[dict[str, Any]]:
        collection = await self._resource_collection()
        mode = self._resource_mode()
        serialized = [
            self._serialize_resource(item, mode=mode, index=index)
            for index, item in enumerate(collection.async_items())
        ]
        return sorted(serialized, key=lambda item: item["resource_id"])

    async def _resource_collection(self) -> Any:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = self._hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            raise KeyError("Home Assistant Lovelace resources are unavailable")
        resources = lovelace_data.resources
        if not getattr(resources, "loaded", True):
            await resources.async_load()
            resources.loaded = True
        return resources

    def _resource_mode(self) -> str:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = self._hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            raise KeyError("Home Assistant Lovelace resources are unavailable")
        return str(lovelace_data.resource_mode)

    def _serialize_resource(
        self, item: dict[str, Any], *, mode: str, index: int
    ) -> dict[str, Any]:
        raw_id = item.get("id")
        resource_id = (
            str(raw_id)
            if raw_id is not None
            else self._synthetic_resource_id(item, index=index)
        )
        return {
            "resource_id": resource_id,
            "id_kind": "storage" if raw_id is not None else "synthetic",
            "resource_mode": mode,
            "type": str(item.get("type", "unknown")),
            "url": self._sanitize_url(str(item.get("url", ""))),
            "source": "home_assistant_lovelace_resource",
        }

    def _synthetic_resource_id(self, item: dict[str, Any], *, index: int) -> str:
        digest = sha1(
            f"{item.get('type', '')}:{item.get('url', '')}:{index}".encode("utf-8")
        ).hexdigest()[:12]
        return f"yaml-{digest}"

    def _sanitize_url(self, url: str) -> str:
        split = urlsplit(url)
        if not split.query:
            return url
        sanitized_query = urlencode(
            [
                (key, _REDACTED if self._is_sensitive_query_key(key) else value)
                for key, value in parse_qsl(split.query, keep_blank_values=True)
            ],
            doseq=True,
        )
        return urlunsplit(
            (split.scheme, split.netloc, split.path, sanitized_query, split.fragment)
        )

    def _is_sensitive_query_key(self, key: str) -> bool:
        normalized = key.casefold().replace("-", "_")
        return normalized in _SENSITIVE_QUERY_KEYS or normalized.endswith("_token")
