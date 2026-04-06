"""Real Home Assistant config flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homeassistant_mcp.const import (
    DEFAULT_DASHBOARD_MODE,
    DEFAULT_TRANSPORT,
    DOMAIN,
    TITLE,
)


async def test_user_flow_creates_default_entry(hass) -> None:
    """Test the user config flow creates the default entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {
        "transport": DEFAULT_TRANSPORT,
        "dashboard_mode": DEFAULT_DASHBOARD_MODE,
    }


async def test_user_flow_aborts_when_entry_exists(hass) -> None:
    """Test the integration remains single-instance."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "transport": DEFAULT_TRANSPORT,
            "dashboard_mode": DEFAULT_DASHBOARD_MODE,
        },
        title=TITLE,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
