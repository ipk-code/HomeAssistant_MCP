"""Read-only Home Assistant discovery helpers for MCP tools."""

from __future__ import annotations

from typing import Any

DEFAULT_DISCOVERY_LIMIT = 100
MAX_DISCOVERY_LIMIT = 200


class HomeAssistantDiscoveryProvider:
    """Expose bounded, read-only Home Assistant discovery views."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    def list_entities(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List entities with optional domain and area filters."""
        domain_filter = arguments.get("domain")
        area_filter = arguments.get("area_id")
        limit = self._limit(arguments)

        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        device_registry = dr.async_get(self._hass)
        entity_registry = er.async_get(self._hass)

        entities = []
        for state in sorted(
            self._hass.states.async_all(), key=lambda item: item.entity_id
        ):
            domain = state.entity_id.split(".", 1)[0]
            if domain_filter and domain != domain_filter:
                continue
            area_id, device_id = self._resolve_entity_links(
                state.entity_id,
                entity_registry=entity_registry,
                device_registry=device_registry,
            )
            if area_filter and area_id != area_filter:
                continue
            entities.append(
                self._serialize_entity(
                    state,
                    area_id=area_id,
                    device_id=device_id,
                )
            )

        items, truncated = self._apply_limit(entities, limit)
        return {"entities": items, "truncated": truncated}

    def list_entity_ids(self) -> list[str]:
        """Return all known entity IDs sorted for completion providers."""
        return sorted(state.entity_id for state in self._hass.states.async_all())

    def search_entities(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search entities by query with optional filters."""
        query = arguments["query"].casefold()
        domain_filter = arguments.get("domain")
        area_filter = arguments.get("area_id")
        device_class_filter = arguments.get("device_class")
        limit = self._limit(arguments)

        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        device_registry = dr.async_get(self._hass)
        entity_registry = er.async_get(self._hass)

        entities = []
        for state in sorted(
            self._hass.states.async_all(), key=lambda item: item.entity_id
        ):
            domain = state.entity_id.split(".", 1)[0]
            if domain_filter and domain != domain_filter:
                continue

            area_id, device_id = self._resolve_entity_links(
                state.entity_id,
                entity_registry=entity_registry,
                device_registry=device_registry,
            )
            if area_filter and area_id != area_filter:
                continue

            device_class = state.attributes.get("device_class")
            if device_class_filter and device_class != device_class_filter:
                continue

            friendly_name = str(state.attributes.get("friendly_name", state.entity_id))
            searchable = (state.entity_id.casefold(), friendly_name.casefold())
            if not any(query in value for value in searchable):
                continue

            entities.append(
                self._serialize_entity(
                    state,
                    area_id=area_id,
                    device_id=device_id,
                )
            )

        items, truncated = self._apply_limit(entities, limit)
        return {"entities": items, "truncated": truncated}

    def list_services(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List registered Home Assistant services."""
        domain_filter = arguments.get("domain")
        limit = self._limit(arguments)
        services = self._hass.services.async_services()

        results = []
        for domain in sorted(services):
            if domain_filter and domain != domain_filter:
                continue
            results.append(
                {
                    "domain": domain,
                    "services": sorted(services[domain].keys()),
                }
            )

        items, truncated = self._apply_limit(results, limit)
        return {"services": items, "truncated": truncated}

    def list_areas(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List configured Home Assistant areas."""
        limit = self._limit(arguments)

        from homeassistant.helpers import area_registry as ar

        area_registry = ar.async_get(self._hass)
        results = []
        for area in sorted(
            area_registry.async_list_areas(), key=lambda item: item.name.casefold()
        ):
            item = {
                "area_id": area.id,
                "name": area.name,
            }
            if area.icon:
                item["icon"] = area.icon
            results.append(item)

        items, truncated = self._apply_limit(results, limit)
        return {"areas": items, "truncated": truncated}

    def list_devices(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List devices with an optional area filter."""
        area_filter = arguments.get("area_id")
        limit = self._limit(arguments)

        from homeassistant.helpers import device_registry as dr

        device_registry = dr.async_get(self._hass)
        results = []
        devices = sorted(
            device_registry.devices.values(),
            key=lambda item: (item.name_by_user or item.name or item.id).casefold(),
        )
        for device in devices:
            if area_filter and device.area_id != area_filter:
                continue
            item = {
                "device_id": device.id,
                "name": device.name_by_user or device.name or device.id,
            }
            if device.area_id:
                item["area_id"] = device.area_id
            if device.manufacturer:
                item["manufacturer"] = device.manufacturer
            if device.model:
                item["model"] = device.model
            results.append(item)

        items, truncated = self._apply_limit(results, limit)
        return {"devices": items, "truncated": truncated}

    def _limit(self, arguments: dict[str, Any]) -> int:
        limit = arguments.get("limit", DEFAULT_DISCOVERY_LIMIT)
        if not isinstance(limit, int):
            return DEFAULT_DISCOVERY_LIMIT
        return max(1, min(limit, MAX_DISCOVERY_LIMIT))

    def _apply_limit(
        self, items: list[dict[str, Any]], limit: int
    ) -> tuple[list[dict[str, Any]], bool]:
        truncated = len(items) > limit
        return items[:limit], truncated

    def _resolve_entity_links(
        self,
        entity_id: str,
        *,
        entity_registry: Any,
        device_registry: Any,
    ) -> tuple[str | None, str | None]:
        entry = entity_registry.async_get(entity_id)
        if entry is None:
            return None, None

        area_id = getattr(entry, "area_id", None)
        device_id = entry.device_id
        if area_id or not device_id:
            return area_id, device_id

        device = device_registry.async_get(device_id)
        return (device.area_id if device is not None else None), device_id

    def _serialize_entity(
        self,
        state: Any,
        *,
        area_id: str | None,
        device_id: str | None,
    ) -> dict[str, Any]:
        domain = state.entity_id.split(".", 1)[0]
        item = {
            "entity_id": state.entity_id,
            "domain": domain,
            "state": state.state,
            "friendly_name": str(
                state.attributes.get("friendly_name", state.entity_id)
            ),
        }
        if area_id:
            item["area_id"] = area_id
        if device_id:
            item["device_id"] = device_id
        device_class = state.attributes.get("device_class")
        if isinstance(device_class, str):
            item["device_class"] = device_class
        unit_of_measurement = state.attributes.get("unit_of_measurement")
        if isinstance(unit_of_measurement, str):
            item["unit_of_measurement"] = unit_of_measurement
        return item
