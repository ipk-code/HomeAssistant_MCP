# Changelog

## 0.3.3

Release focus:

- add read-only frontend panel discovery so MCP clients can inspect sidebar panels without confusing them with Lovelace dashboards

Added:

- read-only frontend panel tools:
  - `hass.list_frontend_panels`
  - `hass.get_frontend_panel`
- read-only frontend panel resources:
  - `hass://frontend/panels`
  - `hass://frontend/panel/{url_path}`
- regression coverage for authenticated frontend panel discovery, resource access, schema validation, and admin-only visibility filtering

Changed:

- bumped the integration package version to `0.3.3`
- threaded authenticated Home Assistant user context through MCP transport and resource reads so admin-only frontend panels are never exposed to non-admin users
- sanitized frontend panel config payloads to avoid surfacing obvious secret-like keys in custom panel metadata
- updated product and API docs to explain the difference between frontend panels, native Lovelace dashboards, and MCP-managed dashboards

Notes:

- the MCP API version remains `1.0.0`
- built-in frontend panels may expose metadata only; this release does not reverse-engineer internal frontend layouts or add any write capability

## 0.3.2

Release focus:

- improve OpenCode compatibility by publishing an object-rooted schema for the full MCP tool catalog

Added:

- regression coverage for both `lovelace.validate_dashboard` argument variants in the spec-driven validator and tool registry tests

Changed:

- bumped the integration package version to `0.3.2`
- updated `lovelace.validate_dashboard` to emit an object-rooted `input_schema` while preserving the existing `oneOf` validation behavior
- refreshed the OpenCode and capability docs to explain the compatibility expectation and troubleshooting flow

Notes:

- the MCP API version remains `1.0.0`
- the functional MCP feature surface from `0.3.1` is unchanged aside from improved remote-client compatibility for tool loading

## 0.3.1

Release focus:

- fix branding asset placement so the custom integration icon appears in HACS and Home Assistant

Added:

- integration-local brand assets in `custom_components/homeassistant_mcp/brand/`:
  - `brand/icon.png`
  - `brand/logo.png`
- a repository-level `brand/icon.png` for HACS validation and presentation checks

Changed:

- bumped the integration package version to `0.3.1`
- updated docs and metadata tests to reference the actual HACS and Home Assistant brand asset locations

Notes:

- the MCP API version remains `1.0.0`
- the functional MCP feature surface from `0.3.0` is unchanged in this release

## 0.3.0

Release focus:

- fix the request-path failures surfaced during live Home Assistant validation
- move managed dashboard repository access off the Home Assistant event loop where it affected MCP requests
- add read-only access to native Home Assistant Lovelace dashboards without mixing them into the MCP-managed repository model

Added:

- read-only native Lovelace dashboard tools:
  - `hass.list_lovelace_dashboards`
  - `hass.get_lovelace_dashboard`
- read-only native Lovelace dashboard resources:
  - `hass://lovelace/dashboards`
  - `hass://lovelace/dashboard/{url_path}`

Changed:

- `resources/read` now returns controlled MCP errors for invalid managed dashboard URIs instead of surfacing a `500`
- managed dashboard repository access used by MCP tools, resources, completions, and prompts now runs through Home Assistant's executor-aware path where needed
- documentation now explains the difference between MCP-managed dashboards and native Home Assistant Lovelace dashboards, and classifies native dashboard access as experimental

Notes:

- the MCP API version remains `1.0.0`
- the integration package version is now `0.3.0`
- native Home Assistant Lovelace dashboard access is read-only and experimental in this release

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
