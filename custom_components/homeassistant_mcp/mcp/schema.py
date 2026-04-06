"""Minimal JSON Schema validator for MCP tool input validation."""

from __future__ import annotations

import re
from typing import Any


class ToolSchemaValidationError(Exception):
    """Raised when tool arguments violate the published API contract."""


class ToolSchemaValidator:
    """Validate MCP tool arguments against a subset of JSON Schema."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self._defs = spec.get("$defs", {})
        self._schemas = {
            tool["name"]: tool["input_schema"] for tool in spec.get("tools", [])
        }

    def validate_tool_arguments(self, tool_name: str, arguments: dict[str, Any]) -> None:
        if tool_name not in self._schemas:
            raise KeyError(f"unknown tool: {tool_name}")
        self._validate(self._schemas[tool_name], arguments, path="$")

    def _validate(self, schema: Any, value: Any, *, path: str) -> None:
        if schema is True:
            return
        if schema is False:
            raise ToolSchemaValidationError(f"{path} is not allowed")
        if not isinstance(schema, dict):
            raise ToolSchemaValidationError(f"invalid schema at {path}")
        if "$ref" in schema:
            return self._validate(self._resolve_ref(schema["$ref"]), value, path=path)
        if "oneOf" in schema:
            errors: list[str] = []
            for candidate in schema["oneOf"]:
                try:
                    self._validate(candidate, value, path=path)
                    return
                except ToolSchemaValidationError as err:
                    errors.append(str(err))
            joined = "; ".join(errors)
            raise ToolSchemaValidationError(f"{path} does not match any allowed schema: {joined}")

        self._validate_common_constraints(schema, value, path=path)

        schema_type = schema.get("type")
        if schema_type == "object":
            self._validate_object(schema, value, path=path)
        elif schema_type == "array":
            self._validate_array(schema, value, path=path)
        elif schema_type == "string":
            self._validate_string(schema, value, path=path)
        elif schema_type == "integer":
            self._validate_integer(schema, value, path=path)
        elif schema_type == "number":
            self._validate_number(schema, value, path=path)
        elif schema_type == "boolean":
            if not isinstance(value, bool):
                raise ToolSchemaValidationError(f"{path} must be a boolean")

    def _validate_common_constraints(self, schema: dict[str, Any], value: Any, *, path: str) -> None:
        if "const" in schema and value != schema["const"]:
            raise ToolSchemaValidationError(f"{path} must equal {schema['const']!r}")
        if "enum" in schema and value not in schema["enum"]:
            raise ToolSchemaValidationError(f"{path} must be one of {schema['enum']!r}")

    def _validate_object(self, schema: dict[str, Any], value: Any, *, path: str) -> None:
        if not isinstance(value, dict):
            raise ToolSchemaValidationError(f"{path} must be an object")
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ToolSchemaValidationError(f"{path}.{key} is required")
        min_properties = schema.get("minProperties")
        if min_properties is not None and len(value) < min_properties:
            raise ToolSchemaValidationError(
                f"{path} must contain at least {min_properties} properties"
            )
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                self._validate(properties[key], item, path=child_path)
                continue
            if additional is False:
                raise ToolSchemaValidationError(f"{child_path} is not allowed")
            if isinstance(additional, dict) or additional in {True, False}:
                self._validate(additional, item, path=child_path)

    def _validate_array(self, schema: dict[str, Any], value: Any, *, path: str) -> None:
        if not isinstance(value, list):
            raise ToolSchemaValidationError(f"{path} must be an array")
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise ToolSchemaValidationError(f"{path} must contain at least {min_items} items")
        max_items = schema.get("maxItems")
        if max_items is not None and len(value) > max_items:
            raise ToolSchemaValidationError(f"{path} must contain at most {max_items} items")
        if "items" in schema:
            for index, item in enumerate(value):
                self._validate(schema["items"], item, path=f"{path}[{index}]")

    def _validate_string(self, schema: dict[str, Any], value: Any, *, path: str) -> None:
        if not isinstance(value, str):
            raise ToolSchemaValidationError(f"{path} must be a string")
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise ToolSchemaValidationError(f"{path} must be at least {min_length} characters")
        max_length = schema.get("maxLength")
        if max_length is not None and len(value) > max_length:
            raise ToolSchemaValidationError(f"{path} must be at most {max_length} characters")
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, value) is None:
            raise ToolSchemaValidationError(f"{path} has an invalid format")

    def _validate_integer(self, schema: dict[str, Any], value: Any, *, path: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolSchemaValidationError(f"{path} must be an integer")
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise ToolSchemaValidationError(f"{path} must be >= {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            raise ToolSchemaValidationError(f"{path} must be <= {maximum}")

    def _validate_number(self, schema: dict[str, Any], value: Any, *, path: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ToolSchemaValidationError(f"{path} must be numeric")
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise ToolSchemaValidationError(f"{path} must be >= {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            raise ToolSchemaValidationError(f"{path} must be <= {maximum}")

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        if not ref.startswith("#/$defs/"):
            raise ToolSchemaValidationError(f"unsupported schema reference: {ref}")
        name = ref.split("/", 2)[2]
        if name not in self._defs:
            raise ToolSchemaValidationError(f"unknown schema definition: {name}")
        return self._defs[name]
