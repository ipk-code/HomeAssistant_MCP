"""Shared pytest fixtures for Home Assistant MCP tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration under test."""
    yield
