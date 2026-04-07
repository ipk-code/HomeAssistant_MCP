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

- All tools listed here are part of the stable v1 dashboard authoring and read-only discovery surface.
- Built-in completions are available for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon`.
- Resources and prompts are not shipped yet.

## Source Of Truth

The exact v1 schemas live in `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`.
