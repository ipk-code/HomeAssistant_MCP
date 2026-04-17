# Tool Catalog

The stable v1 tool surface currently spans the read-only `hass.*` namespace and the mutating `lovelace.*` namespace.

## Admin-Gated Tools

These tools are controlled by the integration setting `Enable admin MCP functions`.

- `hass.create_lovelace_dashboard`
- `hass.update_lovelace_dashboard_metadata`
- `hass.save_lovelace_dashboard_config`
- `hass.delete_lovelace_dashboard`
- `hass.list_template_sensors`
- `hass.get_template_sensor`
- `hass.preview_template_sensor`
- `hass.create_template_sensor`
- `hass.update_template_sensor`
- `hass.delete_template_sensor`

If `Enable admin MCP functions` is disabled, these tools are hidden from `tools/list` and direct calls return a controlled MCP error.

## Home Assistant Discovery Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `hass.list_entities` | no | no | List entities with optional domain and area filters |
| `hass.search_entities` | no | no | Search entities by query with optional domain, area, and device-class filters |
| `hass.list_services` | no | no | List registered Home Assistant services |
| `hass.list_areas` | no | no | List configured Home Assistant areas |
| `hass.list_devices` | no | no | List devices with an optional area filter |

## Native Home Assistant Dashboard Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `hass.list_lovelace_dashboards` | no | no | List standard Home Assistant Lovelace dashboards outside the MCP-managed repository |
| `hass.get_lovelace_dashboard` | no | no | Return one native Home Assistant Lovelace dashboard by `url_path` |
| `hass.create_lovelace_dashboard` | yes | yes | Create a new storage-mode Home Assistant Lovelace dashboard |
| `hass.update_lovelace_dashboard_metadata` | yes | yes | Update metadata for one storage-mode Home Assistant Lovelace dashboard |
| `hass.save_lovelace_dashboard_config` | yes | yes | Replace the config for one storage-mode Home Assistant Lovelace dashboard |
| `hass.delete_lovelace_dashboard` | yes | yes | Delete one storage-mode Home Assistant Lovelace dashboard |

Admin-only note:

- these native Home Assistant write tools require an admin-authenticated Home Assistant user
- these tools are disabled by default until the integration setting `Enable admin MCP functions` is turned on

## Template Sensor Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `hass.list_template_sensors` | no | yes | List Home Assistant template sensor helpers |
| `hass.get_template_sensor` | no | yes | Return one template sensor helper by config entry id |
| `hass.preview_template_sensor` | no | yes | Preview a template sensor helper definition before saving it |
| `hass.create_template_sensor` | yes | yes | Create a new Home Assistant template sensor helper |
| `hass.update_template_sensor` | yes | yes | Update an existing Home Assistant template sensor helper |
| `hass.delete_template_sensor` | yes | yes | Delete a Home Assistant template sensor helper |

Admin-only note:

- these template sensor tools require an admin-authenticated Home Assistant user
- these tools are disabled by default until the integration setting `Enable admin MCP functions` is turned on

## Lovelace Resource Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `hass.list_lovelace_resources` | no | no | List installed Home Assistant Lovelace frontend resources |
| `hass.get_lovelace_resource` | no | no | Return one Lovelace frontend resource by MCP resource identifier |

## Frontend Panel Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `hass.list_frontend_panels` | no | no | List Home Assistant frontend panels visible to the authenticated user |
| `hass.get_frontend_panel` | no | no | Return one frontend panel by `url_path` with the exposed panel metadata and config |

## Dashboard Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `lovelace.list_dashboards` | no | no | List MCP-managed YAML dashboards |
| `lovelace.get_dashboard` | no | no | Return a canonical dashboard document |
| `lovelace.create_dashboard` | yes | no | Create a new YAML dashboard |
| `lovelace.update_dashboard_metadata` | yes | no | Update dashboard metadata only |
| `lovelace.delete_dashboard` | yes | no | Delete a dashboard |
| `lovelace.patch_dashboard` | yes | no | Apply restricted RFC 6902 JSON Patch operations |
| `lovelace.validate_dashboard` | no | no | Validate a dashboard document or patch request |

## View Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `lovelace.list_views` | no | no | List views for a dashboard |
| `lovelace.get_view` | no | no | Return a single view document |
| `lovelace.create_view` | yes | no | Create a new view |
| `lovelace.update_view` | yes | no | Update an existing view |
| `lovelace.delete_view` | yes | no | Delete a view |

## Card Tools

| Tool | Mutation | Admin Gated | Purpose |
|---|---|---|---|
| `lovelace.list_cards` | no | no | List cards for a view |
| `lovelace.get_card` | no | no | Return a single typed card |
| `lovelace.create_card` | yes | no | Insert a new typed card |
| `lovelace.update_card` | yes | no | Replace an existing typed card |
| `lovelace.delete_card` | yes | no | Delete a card |

## Stability

- The `lovelace.*` tool family and the read-only `hass.*` discovery tools are stable in the current dashboard-first MCP surface.
- Built-in completions are available for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon`.
- Built-in resources are available for config, entities, areas, devices, services, managed dashboards, native Lovelace dashboards, Lovelace frontend resources, and frontend panels.
- Built-in prompts are available for dashboard building, review, layout consistency, entity-card mapping, and cleanup audits.
- Native Home Assistant Lovelace dashboard tools are experimental in `0.3.11`; writes are limited to storage dashboards, require an admin-authenticated Home Assistant user, and are disabled by default until the admin-functions toggle is enabled.
- Template sensor tools are experimental in `0.3.11`; they require an admin-authenticated Home Assistant user and are disabled by default until the admin-functions toggle is enabled.
- Lovelace resource tools are experimental in `0.3.11` and remain read-only.
- Frontend panel tools are experimental in `0.3.11` and remain read-only.

## Source Of Truth

The exact v1 schemas live in `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`.
