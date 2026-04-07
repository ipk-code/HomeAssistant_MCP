# API Overview

## Purpose

`HomeAssistant_MCP` exposes Home Assistant Lovelace dashboard authoring capabilities through an MCP-compatible server running inside Home Assistant.

## Current Scope

- Dashboard mode: YAML only
- Transport: stateless Streamable HTTP
- Mutation model: typed tools plus restricted JSON Patch
- Card model: typed helper inputs only
- HTTP endpoint: `/api/homeassistant_mcp`

## Capability Matrix

| Area | Current status | Notes |
|---|---|---|
| Transport | Stable in v1 | `streamable_http_stateless` only |
| Auth | Stable in v1 | Standard Home Assistant authentication |
| MCP methods | Stable in v1 | `initialize`, `tools/list`, `tools/call` |
| Lovelace dashboard tools | Stable in v1 | Dashboard, view, and card CRUD plus validation and patching |
| Resources | Not shipped yet | Planned future expansion |
| Prompts | Not shipped yet | Planned future expansion |
| Completions | Not shipped yet | Planned future expansion |
| OAuth client flow | Not shipped yet | Current remote setup uses bearer tokens |

## Design Boundaries

- MCP clients never provide file system paths.
- Dashboard identity fields are immutable through JSON Patch.
- Stateful transports such as SSE are deferred until the stateless transport is stable.
- The server is currently dashboard-first, not a general-purpose Home Assistant admin surface.

## Runtime Model

- The integration runs inside Home Assistant as a config entry.
- Home Assistant registers an authenticated HTTP view at `/api/homeassistant_mcp`.
- A bundled MCP contract defines the stable v1 tool surface.
- Requests are handled as stateless JSON-RPC messages over HTTP `POST`.

## Main Layers

- `lovelace/validation.py`: input and domain validation
- `lovelace/card_helpers.py`: typed card normalization and rendering
- `lovelace/patch.py`: restricted JSON Patch application
- `lovelace/repository.py`: document persistence and mutation workflow
- `mcp/server.py`: tool contract loading and dispatch
- `mcp/transport.py`: stateless JSON-RPC request handling
