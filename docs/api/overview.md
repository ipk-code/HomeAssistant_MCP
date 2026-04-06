# API Overview

## Purpose

`HomeAssistant_MCP` exposes Home Assistant Lovelace dashboard authoring capabilities through an MCP-compatible server running inside Home Assistant.

## Current Scope

- Dashboard mode: YAML only
- Transport: stateless Streamable HTTP
- Mutation model: typed tools plus restricted JSON Patch
- Card model: typed helper inputs only

## Design Boundaries

- MCP clients never provide file system paths.
- Dashboard identity fields are immutable through JSON Patch.
- Stateful transports such as SSE are deferred until the stateless transport is stable.

## Main Layers

- `lovelace/validation.py`: input and domain validation
- `lovelace/card_helpers.py`: typed card normalization and rendering
- `lovelace/patch.py`: restricted JSON Patch application
- `lovelace/repository.py`: document persistence and mutation workflow
- `mcp/server.py`: tool contract loading and dispatch
- `mcp/transport.py`: stateless JSON-RPC request handling
