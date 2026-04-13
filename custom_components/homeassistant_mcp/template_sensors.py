"""Admin-gated access to Home Assistant template sensor helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.template.const import (
    CONF_ADVANCED_OPTIONS,
    CONF_AVAILABILITY,
)
from homeassistant.components.template.sensor import async_create_preview_sensor
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from .lovelace.errors import LovelaceMCPError


class TemplateSensorProvider:
    """Manage Template sensor helpers through Home Assistant config entries."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    async def list_sensors(
        self, *, user: Any | None = None, limit: int = 200
    ) -> dict[str, Any]:
        self._require_admin(user)
        sensors = [self._serialize_entry(entry) for entry in self._template_entries()]
        sensors.sort(
            key=lambda item: (item["name"].casefold(), item["config_entry_id"])
        )
        truncated = len(sensors) > limit
        return {"sensors": sensors[:limit], "truncated": truncated}

    async def get_sensor(
        self, config_entry_id: str, *, user: Any | None = None
    ) -> dict[str, Any]:
        self._require_admin(user)
        return self._serialize_entry(self._get_entry(config_entry_id))

    async def preview_sensor(
        self, definition: dict[str, Any], *, user: Any | None = None
    ) -> dict[str, Any]:
        self._require_admin(user)
        flat_config = self._flatten_runtime_config(definition)
        self._validate_runtime_config(flat_config)

        entity = async_create_preview_sensor(
            self._hass, flat_config["name"], flat_config
        )
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()

        def _preview_callback(state, attributes, listeners, error) -> None:
            if future.done():
                return
            future.set_result(
                {
                    "state": None if state is None else str(state),
                    "attributes": self._sanitize_json(attributes),
                    "listeners": self._serialize_listeners(listeners),
                    "error": None if error is None else str(error),
                }
            )

        remove = entity.async_start_preview(_preview_callback)
        try:
            result = await asyncio.wait_for(future, timeout=5)
        finally:
            remove()
        return result

    async def create_sensor(
        self, definition: dict[str, Any], *, user: Any | None = None
    ) -> dict[str, Any]:
        self._require_admin(user)
        flow_input = self._flow_input(definition)

        before_ids = {entry.entry_id for entry in self._template_entries()}
        result = await self._hass.config_entries.flow.async_init(
            "template",
            context={"source": SOURCE_USER},
        )
        if result["type"] is not FlowResultType.MENU:
            raise LovelaceMCPError(
                "Template sensor config flow did not start correctly"
            )

        result = await self._hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "sensor"},
        )
        if result["type"] is not FlowResultType.FORM:
            raise LovelaceMCPError(
                "Template sensor config flow did not open the sensor step"
            )

        result = await self._hass.config_entries.flow.async_configure(
            result["flow_id"],
            flow_input,
        )
        if result["type"] is not FlowResultType.CREATE_ENTRY:
            raise LovelaceMCPError(self._format_flow_error(result))

        entry = result.get("result")
        if entry is None:
            created = [
                item
                for item in self._template_entries()
                if item.entry_id not in before_ids
            ]
            if len(created) != 1:
                raise LovelaceMCPError(
                    "Unable to identify created template sensor entry"
                )
            entry = created[0]

        await self._hass.async_block_till_done()
        return self._serialize_entry(entry)

    async def update_sensor(
        self,
        config_entry_id: str,
        patch: dict[str, Any],
        *,
        user: Any | None = None,
    ) -> dict[str, Any]:
        self._require_admin(user)
        entry = self._get_entry(config_entry_id)
        options = dict(entry.options)

        if "name" in patch:
            options["name"] = patch["name"]
        if "state" in patch:
            options["state"] = patch["state"]
        for key in ("unit_of_measurement", "device_class", "state_class", "device_id"):
            if key in patch:
                value = patch[key]
                if value is None:
                    options.pop(key, None)
                else:
                    options[key] = value

        advanced = dict(options.get(CONF_ADVANCED_OPTIONS, {}))
        if "availability" in patch:
            value = patch["availability"]
            if value is None:
                advanced.pop(CONF_AVAILABILITY, None)
            else:
                advanced[CONF_AVAILABILITY] = value
        if advanced:
            options[CONF_ADVANCED_OPTIONS] = advanced
        else:
            options.pop(CONF_ADVANCED_OPTIONS, None)

        self._validate_runtime_config(self._flatten_runtime_config(options))
        self._hass.config_entries.async_update_entry(entry, options=options)
        await self._hass.config_entries.async_reload(entry.entry_id)
        await self._hass.async_block_till_done()
        return self._serialize_entry(self._get_entry(config_entry_id))

    async def delete_sensor(
        self, config_entry_id: str, *, user: Any | None = None
    ) -> dict[str, Any]:
        self._require_admin(user)
        entry = self._get_entry(config_entry_id)
        payload = self._serialize_entry(entry)
        removed = await self._hass.config_entries.async_remove(entry.entry_id)
        if not removed:
            raise LovelaceMCPError("Unable to remove template sensor config entry")
        await self._hass.async_block_till_done()
        return {"deleted": True, "sensor": payload}

    def _template_entries(self) -> list[Any]:
        return [
            entry
            for entry in self._hass.config_entries.async_entries("template")
            if entry.options.get("template_type") == "sensor"
        ]

    def _get_entry(self, config_entry_id: str) -> Any:
        entry = self._hass.config_entries.async_get_entry(config_entry_id)
        if (
            entry is None
            or entry.domain != "template"
            or entry.options.get("template_type") != "sensor"
        ):
            raise LovelaceMCPError(
                f"Unknown template sensor config entry: {config_entry_id}"
            )
        return entry

    def _serialize_entry(self, entry: Any) -> dict[str, Any]:
        entity_registry = er.async_get(self._hass)
        entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        entity_id = entries[0].entity_id if entries else None
        options = dict(entry.options)
        advanced = dict(options.get(CONF_ADVANCED_OPTIONS, {}))
        return {
            "config_entry_id": entry.entry_id,
            "entity_id": entity_id,
            "name": options["name"],
            "state": options["state"],
            "unit_of_measurement": options.get("unit_of_measurement"),
            "device_class": options.get("device_class"),
            "state_class": options.get("state_class"),
            "device_id": options.get("device_id"),
            "availability": advanced.get(CONF_AVAILABILITY),
            "source": "home_assistant_template_helper",
        }

    def _flow_input(self, definition: dict[str, Any]) -> dict[str, Any]:
        flow_input = {
            "name": definition["name"],
            "state": definition["state"],
        }
        for key in ("unit_of_measurement", "device_class", "state_class", "device_id"):
            value = definition.get(key)
            if value is not None:
                flow_input[key] = value
        if definition.get("availability") is not None:
            flow_input[CONF_ADVANCED_OPTIONS] = {
                CONF_AVAILABILITY: definition["availability"]
            }
        return flow_input

    def _flatten_runtime_config(self, definition: dict[str, Any]) -> dict[str, Any]:
        config = {
            "name": definition["name"],
            "state": definition["state"],
        }
        for key in ("unit_of_measurement", "device_class", "state_class", "device_id"):
            value = definition.get(key)
            if value is not None:
                config[key] = value
        advanced = definition.get(CONF_ADVANCED_OPTIONS)
        if isinstance(advanced, dict) and advanced.get(CONF_AVAILABILITY) is not None:
            config[CONF_AVAILABILITY] = advanced[CONF_AVAILABILITY]
        elif definition.get("availability") is not None:
            config[CONF_AVAILABILITY] = definition["availability"]
        return config

    def _validate_runtime_config(self, config: dict[str, Any]) -> None:
        from homeassistant.components.template.config_flow import (
            _validate_state_class,
            _validate_unit,
        )
        from homeassistant.components.template.sensor import SENSOR_CONFIG_ENTRY_SCHEMA

        SENSOR_CONFIG_ENTRY_SCHEMA(config)
        _validate_unit(config)
        _validate_state_class(config)

    def _serialize_listeners(
        self, listeners: dict[str, bool | set[str]] | None
    ) -> dict[str, Any] | None:
        if listeners is None:
            return None
        payload: dict[str, Any] = {}
        for key, value in listeners.items():
            if isinstance(value, set):
                payload[key] = sorted(str(item) for item in value)
            else:
                payload[key] = bool(value)
        return payload

    def _sanitize_json(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): self._sanitize_json(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize_json(item) for item in value]
        return str(value)

    def _format_flow_error(self, result: dict[str, Any]) -> str:
        errors = result.get("errors") or {}
        if not errors:
            return "Template sensor flow did not complete successfully"
        return "; ".join(f"{key}: {value}" for key, value in errors.items())

    def _require_admin(self, user: Any | None) -> None:
        if bool(getattr(user, "is_admin", False)):
            return
        raise LovelaceMCPError(
            "Template sensor MCP functions require a Home Assistant admin user"
        )
