# Changelog

## 0.2.1

Release focus:

- improve the HACS presentation of the integration without changing the MCP runtime surface
- keep the release metadata, startup logs, and documentation aligned with the shipped repository assets

Added:

- a repository icon for HACS built as a playful Home Assistant and MCP mashup
- editable source artwork in `icon.svg`
- HACS-ready raster artwork in `icon.png`

Changed:

- bumped the integration package version to `0.2.1`
- updated release notes and HACS-facing docs to mention the repository icon and current release

Notes:

- the MCP API version remains `1.0.0`
- the integration package version is now `0.2.1`
- the functional MCP feature surface from `0.2.0` is unchanged in this release

## 0.2.0

Release focus:

- expand the MCP server beyond dashboard mutation into a fuller dashboard-first authoring surface
- make the shipped feature set visible in HACS-facing docs and startup logs
- keep the new capability surface read-only outside typed Lovelace mutations

Added:

- read-only `hass.*` discovery tools for entities, services, areas, and devices
- built-in MCP completions for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon`
- built-in MCP resources for:
  - `hass://config`
  - `hass://entities`
  - `hass://areas`
  - `hass://devices`
  - `hass://services`
  - `hass://dashboard/{dashboard_id}`
- built-in dashboard-focused prompts for:
  - `dashboard.builder`
  - `dashboard.review`
  - `dashboard.layout_consistency_review`
  - `dashboard.entity_card_mapping`
  - `dashboard.cleanup_audit`

Changed:

- improved startup logging so Home Assistant logs the loaded integration version and a clear server-started message with endpoint and capability counts
- refreshed the HACS-facing README and the detailed docs to document completions, resources, prompts, capability status, installation verification, and release differences

Notes:

- the MCP API version remains `1.0.0`
- the integration package version is now `0.2.0`
- no OAuth or SSE transport has been added in this release
