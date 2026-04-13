# Documentation

This directory contains the user and contributor documentation for `HomeAssistant_MCP`.

## Start Here

- `../README.md`: HACS-facing overview, install flow, capability summary, and FAQ
- `guides/home-assistant-installation.md`: Home Assistant and HACS setup
- `guides/opencode-integration.md`: OpenCode remote MCP setup and verification

## API Docs

- `api/overview.md`: MCP scope, design boundaries, and architecture layers
- `api/configuration.md`: endpoint, auth model, defaults, and current limitations
- `api/tools.md`: stable v1 discovery and Lovelace tool catalog

## Guides

- `guides/getting-started.md`: local setup and test workflow
- `guides/home-assistant-installation.md`: HACS install, config entry setup, and troubleshooting
- `guides/opencode-integration.md`: remote MCP client configuration and examples
- `guides/security-model.md`: security assumptions and review checklist

## Repository Docs

- `CONTRIBUTING.md`: contribution and development workflow
- `CODE_OF_CONDUCT.md`: contributor behavior expectations
- `../CHANGELOG.md`: release notes and version-to-version feature changes
- `../brand/icon.png`: HACS repository icon asset
- `../icon.svg`: editable icon source artwork
- `../custom_components/homeassistant_mcp/brand/`: Home Assistant integration brand assets

## Audience

- Home Assistant users installing the MCP server from HACS
- OpenCode users connecting to Home Assistant as a remote MCP client
- Contributors implementing new tools, transports, or storage backends
- Reviewers checking API compatibility, testing, and security constraints

## Current v1 Scope

- Home Assistant custom integration
- YAML dashboards only
- stateless Streamable HTTP transport first
- standard Home Assistant auth with bearer tokens for remote access
- read-only `hass.*` discovery tools with bounded result sets
- read-only native Home Assistant Lovelace and frontend panel inspection
- built-in completions for common Home Assistant and Lovelace identifiers
- built-in read-only MCP resources for Home Assistant context, managed dashboards, native Lovelace dashboards, and frontend panels
- built-in dashboard-focused MCP prompts
- typed card helpers only
- RFC 6902 JSON Patch for dashboard patch operations

## Capability Status

- stable in `0.3.8`: discovery tools, typed Lovelace tools, completions, managed-dashboard resources, prompts, stateless HTTP transport, correctly placed HACS/Home Assistant brand assets, broader OpenCode-compatible tool catalog loading, merged security hardening limits, and secure-default admin tool gating
- experimental in `0.3.8`: native Home Assistant Lovelace dashboard access with storage-dashboard writes, Lovelace resource discovery, and read-only Home Assistant frontend panel discovery
- planned next: SSE transport and optional OAuth evaluation
