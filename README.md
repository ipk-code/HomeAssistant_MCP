# Home Assistant MCP

Home Assistant custom integration for MCP-driven Lovelace dashboard authoring.

Current integration version: `0.3.0`

## What It Does

- Runs an MCP server inside Home Assistant.
- Exposes typed Lovelace dashboard, view, and card tools.
- Exposes read-only `hass.*` discovery tools for entities, services, areas, and devices.
- Exposes experimental read-only access to native Home Assistant Lovelace dashboards alongside MCP-managed dashboards.
- Uses stateless Streamable HTTP at `/api/homeassistant_mcp`.
- Uses standard Home Assistant authentication with a long-lived access token for remote clients.
- Keeps dashboard mutations inside a constrained YAML dashboard model with restricted JSON Patch support.

## Transport And Auth

| Setting | Current value |
|---|---|
| HTTP endpoint | `/api/homeassistant_mcp` |
| Transport | `streamable_http_stateless` |
| Home Assistant auth | required |
| OpenCode OAuth mode | `false` |
| Dashboard mode | `yaml` |

Remote MCP clients should send a Home Assistant bearer token. The current OpenCode setup uses `oauth: false` and an `Authorization: Bearer ...` header.

## Install With HACS

Install from the public custom repository:

- `https://github.com/ipk-code/HomeAssistant_MCP`

HACS flow:

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Add `https://github.com/ipk-code/HomeAssistant_MCP` as a custom repository.
4. Install **Home Assistant MCP**.
5. Restart Home Assistant.

## Add The Integration In Home Assistant

1. Open **Settings > Devices & services**.
2. Choose **Add Integration**.
3. Search for `Home Assistant MCP`.
4. Complete the config flow.

After setup, the integration logs `Loaded Home Assistant MCP version 0.3.0 entry ...` and `Home Assistant MCP server version 0.3.0 started successfully ...` when the config entry is active.

Repository icon assets:

- `icon.png` for HACS presentation
- `icon.svg` as the editable source artwork

## Release Notes

Latest release: `0.3.0`

Highlights in `0.3.0` compared with `0.2.1`:

- fixed MCP request-path failures for invalid managed dashboard resource URIs
- moved managed dashboard file access out of the Home Assistant event loop for the affected MCP request paths
- added experimental read-only access to native Home Assistant Lovelace dashboards via dedicated tools and resources

Full release notes: `CHANGELOG.md`

## Use With OpenCode

OpenCode can connect as a remote MCP client with a Home Assistant long-lived access token.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "homeassistant_mcp": {
      "type": "remote",
      "url": "https://ha.example.com/api/homeassistant_mcp",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:HOMEASSISTANT_TOKEN}"
      },
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

## Capability Summary

| Capability | Status | Notes |
|---|---|---|
| `initialize`, `ping`, `tools/list`, `tools/call` | Stable in v1 | Current dashboard authoring MCP method surface |
| Read-only `hass.*` discovery tools | Stable in v1 | Includes `hass.list_entities`, `hass.search_entities`, `hass.list_services`, `hass.list_areas`, `hass.list_devices` |
| Dashboard tools | Stable in v1 | Includes `lovelace.list_dashboards`, `lovelace.get_dashboard`, `lovelace.create_dashboard`, `lovelace.update_dashboard_metadata`, `lovelace.delete_dashboard`, `lovelace.patch_dashboard`, `lovelace.validate_dashboard` |
| Native Lovelace dashboard tools | Experimental in `0.3.0` | Includes `hass.list_lovelace_dashboards` and `hass.get_lovelace_dashboard` for read-only access to standard Home Assistant dashboards |
| View tools | Stable in v1 | Includes `lovelace.list_views`, `lovelace.get_view`, `lovelace.create_view`, `lovelace.update_view`, `lovelace.delete_view` |
| Card tools | Stable in v1 | Includes `lovelace.list_cards`, `lovelace.get_card`, `lovelace.create_card`, `lovelace.update_card`, `lovelace.delete_card` |
| `completion/complete` | Stable in v1 | Built-in completions are available for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon` |
| `resources/list`, `resources/read` | Stable in v1 | Built-in resources are available for config, entities, areas, devices, services, and managed dashboards |
| Native Lovelace dashboard resources | Experimental in `0.3.0` | Includes `hass://lovelace/dashboards` and `hass://lovelace/dashboard/{url_path}` for read-only standard-dashboard access |
| `prompts/list`, `prompts/get` | Stable in v1 | Built-in prompts include `dashboard.builder`, `dashboard.review`, `dashboard.layout_consistency_review`, `dashboard.entity_card_mapping`, and `dashboard.cleanup_audit` |
| OAuth browser-client flow | Not shipped yet | Current deployment uses Home Assistant token auth |

## Capability Status

Stable in `0.3.0`:

- typed Lovelace dashboard, view, and card operations
- read-only `hass.*` discovery tools with bounded result sizes
- built-in completions for common Home Assistant and Lovelace identifiers
- built-in read-only MCP resources for Home Assistant context and managed dashboards, including `hass://config`, `hass://entities`, `hass://areas`, `hass://devices`, `hass://services`, and `hass://dashboard/{dashboard_id}`
- built-in dashboard-focused prompts including `dashboard.builder`, `dashboard.review`, `dashboard.layout_consistency_review`, `dashboard.entity_card_mapping`, and `dashboard.cleanup_audit`
- bundled contract-driven tool schemas
- stateless Streamable HTTP transport
- Home Assistant-authenticated remote access

Experimental in `0.3.0`:

- read-only native Home Assistant Lovelace dashboard access via `hass.list_lovelace_dashboards`, `hass.get_lovelace_dashboard`, `hass://lovelace/dashboards`, and `hass://lovelace/dashboard/{url_path}`

Planned next:

- SSE or other stateful transports
- optional OAuth evaluation for browser-style MCP clients
- native Home Assistant dashboard search and any future write support remain separate follow-up work

## FAQ

**What is this server for?**

It is focused on Lovelace dashboard authoring inside Home Assistant, with read-only discovery tools that help clients inspect entities, services, areas, and devices. It is not a general-purpose Home Assistant admin server.

**What is the difference between MCP-managed and standard dashboards?**

`lovelace.*` tools and `hass://dashboard/{dashboard_id}` operate on MCP-managed dashboards stored under the integration's own repository. Native Home Assistant Lovelace dashboards are exposed separately through `hass.list_lovelace_dashboards`, `hass.get_lovelace_dashboard`, and `hass://lovelace/...` resources so the two models are not mixed accidentally.

**How does authentication work?**

The MCP endpoint uses standard Home Assistant authentication. Remote clients typically use a Home Assistant long-lived access token.

**Does it support OAuth today?**

No. The recommended OpenCode setup keeps `oauth: false` and sends a Home Assistant bearer token.

**What HTTP responses should I expect?**

- `401 Unauthorized`: the endpoint is up and Home Assistant auth is enforcing access
- `404 Not Found`: the integration is not loaded or the URL is wrong
- `405 Method Not Allowed`: the endpoint is loaded and `GET` was sent instead of `POST`

## Troubleshooting

- Enable `custom_components.homeassistant_mcp: debug` in the Home Assistant logger when diagnosing setup or request issues.
- Verify the active build in Home Assistant logs with `Loaded Home Assistant MCP version 0.3.0 entry ...` and `Home Assistant MCP server version 0.3.0 started successfully ...`.
- Confirm clients use `POST` requests to `/api/homeassistant_mcp`.
- Confirm remote clients send a valid Home Assistant bearer token.

## Documentation

- `docs/README.md`
- `docs/api/overview.md`
- `docs/api/configuration.md`
- `docs/api/tools.md`
- `docs/guides/getting-started.md`
- `docs/guides/home-assistant-installation.md`
- `docs/guides/opencode-integration.md`
- `docs/guides/security-model.md`
- `docs/CONTRIBUTING.md`
- `docs/CODE_OF_CONDUCT.md`

## Repository Layout

- `custom_components/homeassistant_mcp/`: integration source code
- `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`: bundled source of truth for the v1 tool contract
- `tests/`: unit and integration tests
- `docs/`: project documentation and contributor guidance

## Testing

```bash
pytest
```

## Security Notes

- The API rejects unknown input fields.
- The API does not accept client-provided file system paths.
- JSON Patch is limited to safe dashboard document scopes.
- Repository writes are atomic to reduce the risk of partial state corruption.
- MCP tool arguments are validated against the published v1 schema before dispatch.
