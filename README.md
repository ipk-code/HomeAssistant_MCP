# Home Assistant MCP

Home Assistant custom integration for MCP-driven Lovelace dashboard authoring.

Current scope:
- Runs as a Home Assistant integration.
- Targets YAML dashboards only in v1.
- Uses stateless Streamable HTTP first.
- Exposes typed Lovelace dashboard mutation tools.
- Uses JSON Patch for whole-dashboard patch operations.

The first implementation step in this repository defines the v1 MCP tool contract in `specs/lovelace_mcp_api_v1.json` and validates it with unit tests.
