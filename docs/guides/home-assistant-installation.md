# Home Assistant Installation

## Prerequisites

- A Home Assistant instance with HACS installed
- Access to the public repository: `https://github.com/ipk-code/HomeAssistant_MCP`

## Install With HACS

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

## After Installation

- The MCP stateless HTTP endpoint is exposed at `/api/homeassistant_mcp`.
- Standard Home Assistant HTTP authentication still applies.
- Dashboard files are managed internally under `.storage/homeassistant_mcp/<config_entry_id>`.
- The published v1 MCP contract is bundled inside the integration at `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`.
- The integration currently supports one config entry with the default stateless transport and YAML dashboard mode.

## Recommended Home Assistant Logger Configuration

For troubleshooting, Home Assistant can enable debug logs for this integration:

```yaml
logger:
  logs:
    custom_components.homeassistant_mcp: debug
```

This integration uses Home Assistant-style logging levels:

- `debug` for normal MCP request flow and setup details
- `info` for entry load and unload lifecycle events
- `warning` for malformed requests and unavailable runtime conditions
- `exception` only for unexpected internal failures

## Troubleshooting

- If setup fails, confirm Home Assistant is running the latest integration files from this repository and then restart Home Assistant.
- `404 Not Found` on `/api/homeassistant_mcp` means the integration has not finished loading.
- `401 Unauthorized` on `/api/homeassistant_mcp` means the HTTP view is registered and Home Assistant auth is working as expected.

## Repository Readiness For HACS

This repository now contains the main HACS-facing pieces:

- `custom_components/homeassistant_mcp/`
- `manifest.json`
- `hacs.json`
- `README.md`

## Next Step

After the integration is installed in Home Assistant, configure OpenCode as a remote MCP client using the guide in `docs/guides/opencode-integration.md`.
