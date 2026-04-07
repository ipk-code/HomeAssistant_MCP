# Home Assistant Installation

## Prerequisites

- A Home Assistant instance with HACS installed
- Access to the public repository: `https://github.com/ipk-code/HomeAssistant_MCP`

## Install With HACS

Current integration version in this repository: `0.3.0`

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Open the overflow menu and choose **Custom repositories**.
4. Add `https://github.com/ipk-code/HomeAssistant_MCP`.
5. Select **Integration** as the category.
6. Install **Home Assistant MCP** from HACS.
7. Restart Home Assistant.

## Add The Integration

1. In Home Assistant, open **Settings > Devices & services**.
2. Choose **Add Integration**.
3. Search for `Home Assistant MCP`.
4. Complete the config flow.

The current config flow creates one default entry with the recommended defaults.

## Verify The Integration Is Loaded

Expected Home Assistant behavior after setup:

- the endpoint `/api/homeassistant_mcp` exists
- `POST` requests require Home Assistant authentication
- the logs show `Loaded Home Assistant MCP version 0.3.0 entry ...`
- the logs show `Home Assistant MCP server version 0.3.0 started successfully ...`

Quick checks:

- `401 Unauthorized` on `POST /api/homeassistant_mcp` means the view is loaded and auth is active
- `405 Method Not Allowed` on `GET /api/homeassistant_mcp` means the view is loaded but `GET` is not supported
- `404 Not Found` means the integration is not loaded or the URL is wrong

## Runtime Details

- The MCP stateless HTTP endpoint is exposed at `/api/homeassistant_mcp`.
- Standard Home Assistant HTTP authentication still applies.
- Dashboard files are managed internally under `.storage/homeassistant_mcp/<config_entry_id>`.
- The published v1 MCP contract is bundled inside the integration at `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`.
- The integration currently supports one config entry with the default stateless transport and YAML dashboard mode.
- Stable in `0.3.0`: discovery tools, completions, managed-dashboard resources, prompts, typed dashboard authoring tools, and HACS presentation assets.
- Experimental in `0.3.0`: read-only native Home Assistant Lovelace dashboard access through dedicated `hass.*` tools and `hass://lovelace/...` resources.

## Recommended Home Assistant Logger Configuration

For troubleshooting, Home Assistant can enable debug logs for this integration:

```yaml
logger:
  logs:
    custom_components.homeassistant_mcp: debug
```

This integration uses Home Assistant-style logging levels:

- `debug` for normal MCP request flow and setup details
- `info` for component startup, HTTP view registration, server-started events, and entry lifecycle events
- `warning` for malformed requests and unavailable runtime conditions
- `exception` only for unexpected internal failures

## Troubleshooting

- If setup fails, confirm Home Assistant is running the latest integration files from this repository and then restart Home Assistant.
- `404 Not Found` on `/api/homeassistant_mcp` means the integration has not finished loading.
- `401 Unauthorized` on `/api/homeassistant_mcp` means the HTTP view is registered and Home Assistant auth is working as expected.
- `405 Method Not Allowed` on `/api/homeassistant_mcp` means the endpoint is loaded and received `GET` instead of `POST`.
- Check the Home Assistant log for `Loaded Home Assistant MCP version ...` and `Home Assistant MCP server version ... started successfully ...` to confirm which integration build is actually running after an update.
- If a standard Lovelace dashboard is visible in Home Assistant but not in `lovelace.list_dashboards`, use the native read-only `hass.list_lovelace_dashboards` tool or the `hass://lovelace/...` resources instead.

## Repository Readiness For HACS

This repository now contains the main HACS-facing pieces:

- `custom_components/homeassistant_mcp/`
- `manifest.json`
- `hacs.json`
- `README.md`
- `icon.png`

## Next Step

After the integration is installed in Home Assistant, configure OpenCode as a remote MCP client using the guide in `docs/guides/opencode-integration.md`.
