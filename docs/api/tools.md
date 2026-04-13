# Tool Catalog

The stable v1 tool surface currently spans the read-only `hass.*` namespace and the mutating `lovelace.*` namespace.

## Home Assistant Discovery Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `hass.list_entities` | no | List entities with optional domain and area filters |
| `hass.search_entities` | no | Search entities by query with optional domain, area, and device-class filters |
| `hass.list_services` | no | List registered Home Assistant services |
| `hass.list_areas` | no | List configured Home Assistant areas |
| `hass.list_devices` | no | List devices with an optional area filter |

## Native Home Assistant Dashboard Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `hass.list_lovelace_dashboards` | no | List standard Home Assistant Lovelace dashboards outside the MCP-managed repository |
| `hass.get_lovelace_dashboard` | no | Return one native Home Assistant Lovelace dashboard by `url_path` |
| `hass.create_lovelace_dashboard` | yes | Create a new storage-mode Home Assistant Lovelace dashboard |
| `hass.update_lovelace_dashboard_metadata` | yes | Update metadata for one storage-mode Home Assistant Lovelace dashboard |
| `hass.save_lovelace_dashboard_config` | yes | Replace the config for one storage-mode Home Assistant Lovelace dashboard |
| `hass.delete_lovelace_dashboard` | yes | Delete one storage-mode Home Assistant Lovelace dashboard |

## Lovelace Resource Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `hass.list_lovelace_resources` | no | List installed Home Assistant Lovelace frontend resources |
| `hass.get_lovelace_resource` | no | Return one Lovelace frontend resource by MCP resource identifier |

## Frontend Panel Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `hass.list_frontend_panels` | no | List Home Assistant frontend panels visible to the authenticated user |
| `hass.get_frontend_panel` | no | Return one frontend panel by `url_path` with the exposed panel metadata and config |

## Dashboard Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `lovelace.list_dashboards` | no | List MCP-managed YAML dashboards |
| `lovelace.get_dashboard` | no | Return a canonical dashboard document |
| `lovelace.create_dashboard` | yes | Create a new YAML dashboard |
| `lovelace.update_dashboard_metadata` | yes | Update dashboard metadata only |
| `lovelace.delete_dashboard` | yes | Delete a dashboard |
| `lovelace.patch_dashboard` | yes | Apply restricted RFC 6902 JSON Patch operations |
| `lovelace.validate_dashboard` | no | Validate a dashboard document or patch request |

## View Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `lovelace.list_views` | no | List views for a dashboard |
| `lovelace.get_view` | no | Return a single view document |
| `lovelace.create_view` | yes | Create a new view |
| `lovelace.update_view` | yes | Update an existing view |
| `lovelace.delete_view` | yes | Delete a view |

## Card Tools

| Tool | Mutation | Purpose |
|---|---|---|
| `lovelace.list_cards` | no | List cards for a view |
| `lovelace.get_card` | no | Return a single typed card |
| `lovelace.create_card` | yes | Insert a new typed card |
| `lovelace.update_card` | yes | Replace an existing typed card |
| `lovelace.delete_card` | yes | Delete a card |

## Stability

- The `lovelace.*` tool family and the read-only `hass.*` discovery tools are stable in the current dashboard-first MCP surface.
- Built-in completions are available for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon`.
- Built-in resources are available for config, entities, areas, devices, services, managed dashboards, native Lovelace dashboards, and frontend panels.
- Built-in resources are available for config, entities, areas, devices, services, managed dashboards, native Lovelace dashboards, Lovelace frontend resources, and frontend panels.
- Built-in prompts are available for dashboard building, review, layout consistency, entity-card mapping, and cleanup audits.
- Native Home Assistant Lovelace dashboard tools are experimental in `0.3.7`; writes are limited to storage dashboards and require an admin-authenticated Home Assistant user.
- Lovelace resource tools are experimental in `0.3.7` and remain read-only.
- Frontend panel tools are experimental in `0.3.7` and remain read-only.

## Source Of Truth

The exact v1 schemas live in `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`.
