# Configuration

## Config Flow

The integration currently creates a single default config entry.

There are no user-editable options in v1.

## Endpoint And Auth Model

| Setting | Value |
|---|---|
| HTTP endpoint | `/api/homeassistant_mcp` |
| Transport | `streamable_http_stateless` |
| Home Assistant auth | required |
| OpenCode OAuth mode | `false` |
| Remote token type | Home Assistant long-lived access token |

## Current Defaults

- `transport`: `streamable_http_stateless`
- `dashboard_mode`: `yaml`
- `endpoint`: `/api/homeassistant_mcp`
- `storage_directory`: `.storage/homeassistant_mcp/<config_entry_id>`
- `max_request_bytes`: `1048576` (1 MiB)
- `single_config_entry`: `true`
- `requires_home_assistant_auth`: `true`
- `open_code_oauth_mode`: `false` recommended for the current token-based setup

## Recommended Settings

- Keep the default stateless transport.
- Keep the default YAML dashboard mode.
- Run only a single config entry.
- Use HTTPS for remote access.
- Pass the Home Assistant token through the MCP client configuration instead of hardcoding it.

## Current Limitations

- YAML dashboards only
- No SSE transport yet
- No user-facing options flow yet
- Storage directory and request-size limit are internal constants, not UI-configurable
- No MCP resources, prompts, or completions yet
- No OAuth flow yet for browser-style MCP clients
