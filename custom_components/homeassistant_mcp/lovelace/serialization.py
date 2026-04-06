"""YAML serialization helpers for rendered Lovelace documents."""

from __future__ import annotations

import re
from typing import Any

from .errors import DashboardValidationError

_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
_RESERVED_SCALARS = {
    "",
    "null",
    "Null",
    "NULL",
    "true",
    "True",
    "TRUE",
    "false",
    "False",
    "FALSE",
    "yes",
    "Yes",
    "YES",
    "no",
    "No",
    "NO",
    "on",
    "On",
    "ON",
    "off",
    "Off",
    "OFF",
    "~",
}


def dump_yaml(data: Any) -> str:
    """Serialize supported Python data into block-style YAML."""
    lines = _serialize(data, 0)
    return "\n".join(lines) + "\n"


def _serialize(value: Any, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [prefix + "{}"]
        lines: list[str] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise DashboardValidationError("YAML object keys must be strings")
            rendered_key = _quote_string(key)
            if _is_multiline_string(item):
                lines.append(f"{prefix}{rendered_key}: |-")
                lines.extend(_serialize_multiline_string(item, indent + 2))
            elif _is_inline_value(item):
                lines.append(f"{prefix}{rendered_key}: {_inline_yaml(item)}")
            else:
                lines.append(f"{prefix}{rendered_key}:")
                lines.extend(_serialize(item, indent + 2))
        return lines

    if isinstance(value, list):
        if not value:
            return [prefix + "[]"]
        lines = []
        for item in value:
            if _is_multiline_string(item):
                lines.append(prefix + "- |-")
                lines.extend(_serialize_multiline_string(item, indent + 2))
            elif _is_inline_value(item):
                lines.append(f"{prefix}- {_inline_yaml(item)}")
            else:
                lines.append(prefix + "-")
                lines.extend(_serialize(item, indent + 2))
        return lines

    return [prefix + _inline_yaml(value)]


def _is_inline_value(value: Any) -> bool:
    return _is_scalar(value) or value == {} or value == []


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_multiline_string(value: Any) -> bool:
    return isinstance(value, str) and "\n" in value


def _inline_yaml(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise DashboardValidationError("YAML serializer does not allow NaN or infinity")
        return repr(value)
    if isinstance(value, str):
        return _quote_string(value)
    if value == {}:
        return "{}"
    if value == []:
        return "[]"
    raise DashboardValidationError(f"unsupported YAML scalar type: {type(value)!r}")


def _quote_string(value: str) -> str:
    if (
        _SAFE_SCALAR_RE.fullmatch(value)
        and value not in _RESERVED_SCALARS
        and not value[0].isdigit()
    ):
        return value
    return "'" + value.replace("'", "''") + "'"


def _serialize_multiline_string(value: str, indent: int) -> list[str]:
    prefix = " " * indent
    return [prefix + line if line else prefix for line in value.splitlines()]
