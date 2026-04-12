"""Restricted RFC 6902 JSON Patch support for dashboard documents."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .errors import PatchApplicationError

# CWE-400: Cap operations to prevent CPU exhaustion from large patch payloads
MAX_PATCH_OPERATIONS = 50


def _decode_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _split_pointer(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise PatchApplicationError("JSON pointer must start with '/'")
    parts = [_decode_token(part) for part in pointer.split("/")[1:]]
    if not parts or parts[0] not in {"metadata", "views"}:
        raise PatchApplicationError("JSON Patch may only target /metadata or /views")
    return parts


def validate_patch_operation(operation: dict[str, Any]) -> None:
    """Reject patch operations that target immutable identifiers or modes."""
    path_tokens = _split_pointer(operation["path"])
    _validate_mutable_tokens(path_tokens, field_name="path")
    if "from" in operation:
        _validate_mutable_tokens(_split_pointer(operation["from"]), field_name="from")


def _validate_mutable_tokens(tokens: list[str], *, field_name: str) -> None:
    if tokens[0] == "metadata" and len(tokens) > 1 and tokens[1] in {
        "dashboard_id",
        "mode",
        "url_path",
    }:
        raise PatchApplicationError(f"{field_name} targets immutable dashboard metadata")
    if tokens[0] == "views":
        if len(tokens) > 2 and tokens[2] == "view_id":
            raise PatchApplicationError(f"{field_name} targets immutable view_id")
        if len(tokens) > 4 and tokens[4] == "card_id":
            raise PatchApplicationError(f"{field_name} targets immutable card_id")


def _container_and_token(document: Any, pointer: str) -> tuple[Any, str]:
    parts = _split_pointer(pointer)
    current = document
    for token in parts[:-1]:
        current = _resolve_token(current, token)
    return current, parts[-1]


def _resolve_token(current: Any, token: str) -> Any:
    if isinstance(current, list):
        index = _parse_index(token, allow_end=False)
        try:
            return current[index]
        except IndexError as err:
            raise PatchApplicationError(f"list index out of range: {token}") from err
    if isinstance(current, dict):
        if token not in current:
            raise PatchApplicationError(f"object key not found: {token}")
        return current[token]
    raise PatchApplicationError("cannot traverse into scalar values")


def _parse_index(token: str, *, allow_end: bool, length: int | None = None) -> int:
    if token == "-":
        if not allow_end or length is None:
            raise PatchApplicationError("'-' is only valid when appending to a list")
        return length
    if not token.isdigit():
        raise PatchApplicationError(f"invalid list index: {token}")
    index = int(token)
    if index < 0:
        raise PatchApplicationError(f"invalid list index: {token}")
    return index


def _add(container: Any, token: str, value: Any) -> None:
    if isinstance(container, list):
        index = _parse_index(token, allow_end=True, length=len(container))
        if index > len(container):
            raise PatchApplicationError(f"list index out of range: {token}")
        container.insert(index, deepcopy(value))
        return
    if isinstance(container, dict):
        container[token] = deepcopy(value)
        return
    raise PatchApplicationError("add target must be a list or object")


def _replace(container: Any, token: str, value: Any) -> None:
    if isinstance(container, list):
        index = _parse_index(token, allow_end=False)
        if index >= len(container):
            raise PatchApplicationError(f"list index out of range: {token}")
        container[index] = deepcopy(value)
        return
    if isinstance(container, dict):
        if token not in container:
            raise PatchApplicationError(f"object key not found: {token}")
        container[token] = deepcopy(value)
        return
    raise PatchApplicationError("replace target must be a list or object")


def _remove(container: Any, token: str) -> Any:
    if isinstance(container, list):
        index = _parse_index(token, allow_end=False)
        if index >= len(container):
            raise PatchApplicationError(f"list index out of range: {token}")
        return container.pop(index)
    if isinstance(container, dict):
        if token not in container:
            raise PatchApplicationError(f"object key not found: {token}")
        return container.pop(token)
    raise PatchApplicationError("remove target must be a list or object")


def _read(document: Any, pointer: str) -> Any:
    current = document
    for token in _split_pointer(pointer):
        current = _resolve_token(current, token)
    return deepcopy(current)


def apply_json_patch(
    document: dict[str, Any], operations: list[dict[str, Any]]
) -> tuple[dict[str, Any], int]:
    """Apply restricted RFC 6902 operations to a dashboard document."""
    if len(operations) > MAX_PATCH_OPERATIONS:
        raise PatchApplicationError(
            f"patch exceeds maximum of {MAX_PATCH_OPERATIONS} operations"
        )
    patched = deepcopy(document)
    applied = 0
    for operation in operations:
        op = operation.get("op")
        path = operation.get("path")
        if not isinstance(op, str) or not isinstance(path, str):
            raise PatchApplicationError("each operation must include string op and path")
        validate_patch_operation(operation)

        if op == "test":
            if _read(patched, path) != operation.get("value"):
                raise PatchApplicationError(f"test operation failed for {path}")
            applied += 1
            continue

        if op == "copy":
            _add(*_container_and_token(patched, path), _read(patched, operation["from"]))
            applied += 1
            continue

        if op == "move":
            source_container, source_token = _container_and_token(patched, operation["from"])
            moved = _remove(source_container, source_token)
            _add(*_container_and_token(patched, path), moved)
            applied += 1
            continue

        container, token = _container_and_token(patched, path)
        if op == "add":
            _add(container, token, operation.get("value"))
        elif op == "replace":
            _replace(container, token, operation.get("value"))
        elif op == "remove":
            _remove(container, token)
        else:
            raise PatchApplicationError(f"unsupported patch operation: {op}")
        applied += 1
    return patched, applied
