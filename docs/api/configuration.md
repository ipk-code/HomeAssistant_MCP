# Configuration

## Config Flow

The integration currently creates a single default config entry.

There are no user-editable options in v1.

## Current Defaults

- `transport`: `streamable_http_stateless`
- `dashboard_mode`: `yaml`
- `endpoint`: `/api/homeassistant_mcp`
- `storage_directory`: `.storage/homeassistant_mcp/<config_entry_id>`
- `max_request_bytes`: `1048576` (1 MiB)
- `single_config_entry`: `true`

## Recommended Settings

- Keep the default stateless transport.
- Keep the default YAML dashboard mode.
- Run only a single config entry.

## Current Limitations

- YAML dashboards only
- No SSE transport yet
- No user-facing options flow yet
- Storage directory and request-size limit are internal constants, not UI-configurable
