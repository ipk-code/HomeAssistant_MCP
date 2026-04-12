# API Overview

## Purpose

`HomeAssistant_MCP` exposes Home Assistant Lovelace dashboard authoring capabilities through an MCP-compatible server running inside Home Assistant.

## Current Scope

- Dashboard mode: YAML only
- Transport: stateless Streamable HTTP
- Mutation model: typed tools plus restricted JSON Patch
- Card model: typed helper inputs only
- Read-only discovery model: bounded `hass.*` inspection tools
- HTTP endpoint: `/api/homeassistant_mcp`

## Capability Matrix

| Area | Current status | Notes |
|---|---|---|
| Transport | Stable in v1 | `streamable_http_stateless` only |
| Auth | Stable in v1 | Standard Home Assistant authentication |
| MCP methods | Stable in v1 | `initialize`, `ping`, `tools/list`, `tools/call` |
| Read-only Home Assistant discovery tools | Stable in v1 | `hass.list_entities`, `hass.search_entities`, `hass.list_services`, `hass.list_areas`, `hass.list_devices` |
| Frontend panel tools | Experimental in `0.3.4` | `hass.list_frontend_panels` and `hass.get_frontend_panel` expose Home Assistant sidebar panels read-only |
| Lovelace dashboard tools | Stable in v1 | Dashboard, view, and card CRUD plus validation and patching |
| Native Lovelace dashboard tools | Experimental in `0.3.4` | `hass.list_lovelace_dashboards`, `hass.get_lovelace_dashboard`, and the storage-dashboard write tools expose standard Home Assistant dashboards through a protected native surface |
| Resources | Stable in v1 | `resources/list` and `resources/read` expose config, entities, areas, devices, services, and `hass://dashboard/{dashboard_id}` |
| Native Lovelace dashboard resources | Experimental in `0.3.4` | `hass://lovelace/dashboards` and `hass://lovelace/dashboard/{url_path}` expose standard Home Assistant dashboards for inspection |
| Frontend panel resources | Experimental in `0.3.4` | `hass://frontend/panels` and `hass://frontend/panel/{url_path}` expose sidebar panel metadata read-only |
| Prompts | Stable in v1 | `prompts/list` and `prompts/get` expose `dashboard.builder`, `dashboard.review`, `dashboard.layout_consistency_review`, `dashboard.entity_card_mapping`, and `dashboard.cleanup_audit` |
| Completions | Stable in v1 | `completion/complete` provides built-in suggestions for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon` |
| OAuth client flow | Not shipped yet | Current remote setup uses bearer tokens |

## Design Boundaries

- MCP clients never provide file system paths.
- Dashboard identity fields are immutable through JSON Patch.
- Stateful transports such as SSE are deferred until the stateless transport is stable.
- The server is currently dashboard-first, not a general-purpose Home Assistant admin surface.
- Discovery tools are read-only and enforce bounded response sizes.
- Resources are read-only and expose bounded Home Assistant context plus managed dashboards, native Lovelace dashboards, and frontend panels where available.
- Prompts are advisory only and guide clients toward the existing typed tools and resources instead of adding hidden write paths.
- Native Home Assistant Lovelace dashboard access is intentionally separated from MCP-managed dashboards; writes are limited to storage dashboards and require an admin user.
- Frontend panel discovery remains read-only and preserves Home Assistant admin-only visibility rules.

## Runtime Model

- The integration runs inside Home Assistant as a config entry.
- Home Assistant registers an authenticated HTTP view at `/api/homeassistant_mcp`.
- A bundled MCP contract defines the stable v1 tool surface.
- Tool input schemas are emitted as object-rooted JSON Schema documents for broad remote-client compatibility.
- Requests are handled as stateless JSON-RPC messages over HTTP `POST`.
- Resources, prompts, and completions are provided by dedicated registries so new capabilities can be added without rewriting the transport.

## Capability Status

- stable in `0.3.4`: discovery tools, typed Lovelace tools, completions, managed-dashboard resources, prompts, stateless HTTP transport, correctly placed HACS/Home Assistant brand assets, and broader OpenCode-compatible tool catalog loading
- experimental in `0.3.4`: native Home Assistant Lovelace dashboard access with storage-dashboard writes and read-only frontend panel discovery
- planned next: SSE transport and optional OAuth evaluation

## Main Layers

- `lovelace/validation.py`: input and domain validation
- `lovelace/card_helpers.py`: typed card normalization and rendering
- `lovelace/patch.py`: restricted JSON Patch application
- `lovelace/repository.py`: document persistence and mutation workflow
- `mcp/server.py`: tool contract loading and dispatch
- `mcp/transport.py`: stateless JSON-RPC request handling
