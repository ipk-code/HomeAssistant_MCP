# Home Assistant Installation

## Prerequisites

- A Home Assistant instance with HACS installed
- This repository published to a GitHub repository that HACS can access

## Install With HACS

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Open the overflow menu and choose **Custom repositories**.
4. Add the repository URL for this project.
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

## Repository Readiness For HACS

This repository now contains the main HACS-facing pieces:

- `custom_components/homeassistant_mcp/`
- `manifest.json`
- `hacs.json`
- `README.md`

## Remaining Publishing Requirement

To install through HACS, the repository still needs to be pushed to a reachable GitHub remote. HACS installs from the published repository, not from the local filesystem path.
