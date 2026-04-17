# Changelog

## 0.3.11

Release focus:

- restore full OpenCode tool-catalog compatibility without changing the `lovelace.validate_dashboard` runtime API

Added:

- regression coverage for OpenAI-compatible top-level tool schemas in the bundled contract, registry serialization, transport responses, and real Home Assistant HTTP `tools/list` output
- regression coverage for invalid `lovelace.validate_dashboard` argument combinations so document validation and patch validation stay mutually exclusive

Changed:

- bumped the integration package version to `0.3.11`
- updated `lovelace.validate_dashboard` to publish a top-level object schema without top-level `oneOf`, `anyOf`, `allOf`, `enum`, or `not`
- moved the exact `lovelace.validate_dashboard` argument-variant enforcement into server-side validation so both supported request shapes remain available to MCP clients
- refreshed the README, install guide, API docs, and OpenCode guide to explain the OpenAI-function-compatible schema requirement and troubleshooting flow

Notes:

- the MCP API version remains `1.0.0`
- the functional MCP capability surface is unchanged aside from improved remote-client compatibility for `tools/list`

## 0.3.10

Release focus:

- make the admin-function toggle take effect immediately after changing integration options and tighten the docs around admin-gated tool visibility

Changed:

- bumped the integration package version to `0.3.10`
- switched the integration options flow to `OptionsFlowWithReload` so changing `Enable admin MCP functions` reloads the integration automatically
- expanded the tool catalog and FAQ/troubleshooting docs to explicitly list every admin-gated tool and explain what to check when those tools are not visible

Notes:

- the MCP API version remains `1.0.0`
- the admin-function toggle still defaults to `false`

## 0.3.9

Release focus:

- add admin-gated Home Assistant template sensor helper management on top of the secure-default admin function toggle

Added:

- template sensor helper tools:
  - `hass.list_template_sensors`
  - `hass.get_template_sensor`
  - `hass.preview_template_sensor`
  - `hass.create_template_sensor`
  - `hass.update_template_sensor`
  - `hass.delete_template_sensor`
- regression coverage for template sensor preview, create, list, get, update, delete, transport gating, and HTTP lifecycle behavior

Changed:

- bumped the integration package version to `0.3.9`
- extended the admin-function toggle to cover template sensor helper tools in addition to native Lovelace write tools
- used Home Assistant template-helper config entries instead of YAML writes for template sensor management

Notes:

- the MCP API version remains `1.0.0`
- admin-only MCP tools stay disabled by default until `enable_admin_functions` is enabled in the integration configuration

## 0.3.8

Release focus:

- add a secure-default integration toggle that disables admin-only MCP functions unless the Home Assistant owner explicitly enables them

Added:

- config-entry and options-flow setting: `enable_admin_functions`
- regression coverage for the secure default, options flow updates, hidden admin tools, and direct-call rejection when disabled

Changed:

- bumped the integration package version to `0.3.8`
- disabled admin-only MCP functions by default in new config entries
- hid admin-only MCP tools from `tools/list` when the integration toggle is off
- rejected direct calls to disabled admin-only tools with a controlled MCP error instead of exposing them implicitly

Notes:

- the MCP API version remains `1.0.0`
- current admin-only tools covered by the toggle are:
  - `hass.create_lovelace_dashboard`
  - `hass.update_lovelace_dashboard_metadata`
  - `hass.save_lovelace_dashboard_config`
  - `hass.delete_lovelace_dashboard`

## 0.3.7

Release focus:

- merge the follow-up `security_review_1204` hardening branch and publish the additional request-validation improvements

Added:

- regression coverage for protocol-relative URL rejection, finite-number validation, and control-character escaping in log sanitization

Changed:

- bumped the integration package version to `0.3.7`
- rejected protocol-relative URLs such as `//example.com` in URL validation to prevent open-redirect style misuse
- rejected `NaN`, `Infinity`, and `-Infinity` values in numeric validation so persisted documents stay JSON-safe and portable
- sanitized all ASCII control characters in logged user input using hex escapes instead of only escaping CR/LF

Notes:

- the MCP API version remains `1.0.0`
- these changes further harden the existing feature surface and do not add new MCP capabilities

## 0.3.6

Release focus:

- merge the reviewed security hardening branch into the mainline release and document the new operational limits

Added:

- regression coverage for stricter Accept-header parsing, request-size prechecks, dashboard/view/card caps, patch-operation caps, UUID card IDs, and owner-only storage permissions

Changed:

- bumped the integration package version to `0.3.6`
- tightened Accept header parsing so only real JSON-capable media types are accepted
- rejected oversized requests before reading the body when `Content-Length` already exceeds the server limit
- sanitized user-controlled values before writing them into MCP transport logs
- capped card nesting depth, JSON patch operations, views per dashboard, and cards per view to reduce denial-of-service risk
- switched generated card IDs from a process-local counter to `uuid4`-based identifiers to avoid collisions across restarts
- applied owner-only permissions to the managed dashboard storage directories on supported filesystems

Notes:

- the MCP API version remains `1.0.0`
- these changes harden the existing feature surface; they do not add new public MCP capabilities beyond the already documented `0.3.5` tools and resources

## 0.3.5

Release focus:

- add read-only Lovelace resource discovery so MCP clients can inspect installed frontend resource URLs and types without guessing from dashboards alone

Added:

- Lovelace resource discovery tools:
  - `hass.list_lovelace_resources`
  - `hass.get_lovelace_resource`
- Lovelace resource discovery resources:
  - `hass://lovelace/resources`
  - `hass://lovelace/resource/{resource_id}`
- regression coverage for storage and synthetic resource identifiers, URL sanitization, resource registry exposure, and HTTP transport access

Changed:

- bumped the integration package version to `0.3.5`
- extended built-in MCP resources to expose the Home Assistant Lovelace resource inventory separately from dashboard documents
- sanitized obvious secret-like query parameters in exposed Lovelace resource URLs before returning them through MCP

Notes:

- the MCP API version remains `1.0.0`
- YAML-mode resource identifiers are synthetic MCP identifiers derived from the current resource list and remain read-only

## 0.3.4

Release focus:

- add admin-gated native Home Assistant Lovelace dashboard writes for storage dashboards while preserving read-only safety for protected dashboard types

Added:

- native Home Assistant dashboard write tools:
  - `hass.create_lovelace_dashboard`
  - `hass.update_lovelace_dashboard_metadata`
  - `hass.save_lovelace_dashboard_config`
  - `hass.delete_lovelace_dashboard`
- regression coverage for native dashboard create, metadata update, config save, delete, and admin-only visibility filtering

Changed:

- bumped the integration package version to `0.3.4`
- native Home Assistant Lovelace dashboard reads now respect `require_admin` so non-admin MCP callers do not learn about protected dashboards
- native dashboard writes are limited to storage dashboards and reject the default, YAML, and auto-generated dashboard variants

Notes:

- the MCP API version remains `1.0.0`
- native dashboard writes remain experimental and intentionally do not add generic Home Assistant admin mutation capabilities beyond Lovelace storage dashboards

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
