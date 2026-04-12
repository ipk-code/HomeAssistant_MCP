"""Domain errors for Lovelace dashboard authoring."""

from __future__ import annotations


class LovelaceMCPError(Exception):
    """Base error for the Lovelace MCP domain."""


class DashboardValidationError(LovelaceMCPError):
    """Raised when dashboard input is invalid."""


class DashboardNotFoundError(LovelaceMCPError):
    """Raised when a dashboard does not exist."""


class DashboardConflictError(LovelaceMCPError):
    """Raised when a dashboard already exists or a version mismatches."""


class PatchApplicationError(LovelaceMCPError):
    """Raised when JSON Patch application fails."""


class DashboardPermissionError(LovelaceMCPError):
    """Raised when the caller is not allowed to mutate a dashboard."""


class UnsupportedDashboardOperationError(LovelaceMCPError):
    """Raised when a dashboard cannot be changed through the native MCP tools."""
