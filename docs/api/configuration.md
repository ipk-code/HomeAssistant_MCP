# Configuration

## Config Flow

The integration currently creates a single default config entry.

User-facing setting:

- `enable_admin_functions`: `false` by default

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
- `discovery_default_limit`: `100`
- `discovery_max_limit`: `200`
- `completion_max_values`: `25`
- `max_card_nesting_depth`: `5`
- `max_patch_operations`: `50`
- `max_views_per_dashboard`: `50`
- `max_cards_per_view`: `200`
- `single_config_entry`: `true`
- `enable_admin_functions`: `false`
- `requires_home_assistant_auth`: `true`
- `open_code_oauth_mode`: `false` recommended for the current token-based setup

## Recommended Settings

- Keep the default stateless transport.
- Keep the default YAML dashboard mode.
- Keep `enable_admin_functions` disabled unless you explicitly want MCP clients to create, update, or delete native Home Assistant dashboards.
- Run only a single config entry.
- Use discovery tool `limit` arguments when clients do not need the full result set.
- Pass current tool arguments in the MCP completion `ref.arguments` payload when completing dependent identifiers like `view_id` or `card_id`.
- Use `resources/read` for large, read-only context like entity inventories or a managed dashboard document.
- Use `hass.get_lovelace_dashboard` or `hass://lovelace/dashboard/{url_path}` when you need to inspect a standard Home Assistant dashboard that is not MCP-managed.
- Use the native Lovelace write tools only for storage dashboards, only with an admin-authenticated MCP client, and only after enabling `enable_admin_functions` in the integration setup or options flow.
- Use `hass.list_lovelace_resources` or `hass://lovelace/resources` when you need to inspect installed Lovelace frontend resources such as custom card bundles.
- Use `hass.get_frontend_panel` or `hass://frontend/panel/{url_path}` when a Home Assistant sidebar item is not a Lovelace dashboard and you need its exposed panel metadata or config.
- Use `prompts/get` when you want an MCP-native workflow scaffold before calling `lovelace.*` tools.
- Use HTTPS for remote access.
- Pass the Home Assistant token through the MCP client configuration instead of hardcoding it.

## Current Limitations

- YAML dashboards only
- MCP-managed dashboard mutations remain available; native Home Assistant Lovelace writes are limited to storage dashboards and require admin authentication
- Admin-only MCP tools are disabled by default until `enable_admin_functions` is turned on in the integration configuration
- Frontend panel discovery is read-only and follows the caller's Home Assistant admin visibility
- Built-in frontend panels may expose metadata only; internal frontend layouts are not generally available through Home Assistant APIs
- Lovelace resource discovery is read-only; YAML-mode resource identifiers are synthetic MCP identifiers rather than persistent Home Assistant IDs
- No SSE transport yet
- Storage directory and request-size limit are internal constants, not UI-configurable
- No OAuth flow yet for browser-style MCP clients

## Capability Status

- stable in `0.3.8`: discovery tools, typed Lovelace tools, completions, managed-dashboard resources, prompts, stateless HTTP transport, correctly placed HACS/Home Assistant brand assets, broader OpenCode-compatible tool catalog loading, merged security hardening limits, and secure-default admin tool gating
- experimental in `0.3.8`: native Home Assistant Lovelace dashboard access with storage-dashboard writes, Lovelace resource discovery, and read-only frontend panel discovery
- planned next: SSE transport and optional OAuth evaluation
