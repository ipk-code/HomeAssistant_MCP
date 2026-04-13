"""Constants for the Home Assistant MCP integration."""

DOMAIN = "homeassistant_mcp"
TITLE = "Home Assistant MCP"
INTEGRATION_VERSION = "0.3.9"
API_VERSION = "1.0.0"
DEFAULT_TRANSPORT = "streamable_http_stateless"
DEFAULT_DASHBOARD_MODE = "yaml"
CONF_ENABLE_ADMIN_FUNCTIONS = "enable_admin_functions"
DEFAULT_ENABLE_ADMIN_FUNCTIONS = False
STREAMABLE_HTTP_API = "/api/homeassistant_mcp"
STORAGE_DIRECTORY = ".storage/homeassistant_mcp"
MAX_REQUEST_BYTES = 1048576

ADMIN_REQUIRED_TOOLS = {
    "hass.create_lovelace_dashboard",
    "hass.update_lovelace_dashboard_metadata",
    "hass.save_lovelace_dashboard_config",
    "hass.delete_lovelace_dashboard",
    "hass.list_template_sensors",
    "hass.get_template_sensor",
    "hass.preview_template_sensor",
    "hass.create_template_sensor",
    "hass.update_template_sensor",
    "hass.delete_template_sensor",
}
