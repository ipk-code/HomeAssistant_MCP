# Home Assistant MCP

Home Assistant custom integration for MCP-driven Lovelace dashboard authoring.

Current integration version: `0.1.1`

## What It Does

- Runs an MCP server inside Home Assistant.
- Exposes typed Lovelace dashboard, view, and card tools.
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

After setup, the integration logs `Loaded Home Assistant MCP version 0.1.1 entry ...` when the config entry is active.

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
| `initialize`, `tools/list`, `tools/call` | Stable in v1 | Current MCP method surface |
| Dashboard tools | Stable in v1 | Includes `lovelace.list_dashboards`, `lovelace.get_dashboard`, `lovelace.create_dashboard`, `lovelace.update_dashboard_metadata`, `lovelace.delete_dashboard`, `lovelace.patch_dashboard`, `lovelace.validate_dashboard` |
| View tools | Stable in v1 | Includes `lovelace.list_views`, `lovelace.get_view`, `lovelace.create_view`, `lovelace.update_view`, `lovelace.delete_view` |
| Card tools | Stable in v1 | Includes `lovelace.list_cards`, `lovelace.get_card`, `lovelace.create_card`, `lovelace.update_card`, `lovelace.delete_card` |
| Resources, prompts, completions | Not shipped yet | Planned after the v1 dashboard authoring baseline |
| OAuth browser-client flow | Not shipped yet | Current deployment uses Home Assistant token auth |

## Stable And Planned Scope

Stable in v1:

- typed Lovelace dashboard, view, and card operations
- bundled contract-driven tool schemas
- stateless Streamable HTTP transport
- Home Assistant-authenticated remote access

Not available yet:

- read-only `hass.*` discovery tools
- MCP resources
- MCP prompts
- MCP completions
- SSE or other stateful transports

## FAQ

**What is this server for?**

It is focused on Lovelace dashboard authoring inside Home Assistant. It is not a general-purpose Home Assistant admin server.

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
- Verify the active build in Home Assistant logs with `Loaded Home Assistant MCP version 0.1.1 entry ...`.
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
