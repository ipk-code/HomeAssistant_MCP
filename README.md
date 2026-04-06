# Home Assistant MCP

Home Assistant custom integration for MCP-driven Lovelace dashboard authoring.

## Current Scope

- Runs as a Home Assistant integration.
- Targets YAML dashboards only in v1.
- Uses stateless Streamable HTTP first.
- Exposes typed Lovelace dashboard mutation tools.
- Uses JSON Patch for whole-dashboard patch operations.

## Repository Layout

- `custom_components/homeassistant_mcp/`: integration source code
- `specs/lovelace_mcp_api_v1.json`: source of truth for the v1 tool contract
- `tests/`: unit tests for validation, patching, repository behavior, and transport handling
- `docs/`: project documentation and contributor guidance

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

## Testing

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Security Notes

- The API rejects unknown input fields.
- The API does not accept client-provided file system paths.
- JSON Patch is limited to safe dashboard document scopes.
- Repository writes are atomic to reduce the risk of partial state corruption.
- MCP tool arguments are validated against the published v1 schema before dispatch.

## Status

The project currently contains:

- a versioned API contract
- a YAML dashboard repository abstraction
- typed card helper normalization
- true YAML rendering for generated dashboard files
- restricted JSON Patch support
- a stateless MCP-style transport handler

## Home Assistant And HACS

Install from HACS using the public custom repository:

- `https://github.com/ipk-code/HomeAssistant_MCP`

After installation, add the integration in **Settings > Devices & services**.

For complete setup instructions:

- `docs/guides/home-assistant-installation.md`
- `docs/guides/opencode-integration.md`

## Logging

The integration now emits Home Assistant-style logs for:

- component and config-entry lifecycle events
- HTTP view registration
- malformed MCP requests
- MCP tool execution failures
- unexpected internal exceptions

To debug it in Home Assistant:

```yaml
logger:
  logs:
    custom_components.homeassistant_mcp: debug
```
