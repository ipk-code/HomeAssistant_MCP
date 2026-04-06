# Documentation

This directory contains the working documentation for `HomeAssistant_MCP`.

## Contents

- `CONTRIBUTING.md`: contribution and development workflow
- `CODE_OF_CONDUCT.md`: contributor behavior expectations
- `api/configuration.md`: current defaults, limits, and configuration behavior
- `api/overview.md`: MCP API shape and transport scope
- `api/tools.md`: v1 Lovelace tool catalog
- `guides/getting-started.md`: local setup and test workflow
- `guides/home-assistant-installation.md`: HACS and Home Assistant installation steps
- `guides/security-model.md`: security assumptions and review checklist

## Audience

- Home Assistant integrators who want to run the MCP server
- Contributors implementing new tools or storage backends
- Reviewers checking API compatibility, testing, and security constraints

## Versioning

The current implementation target is v1:

- Home Assistant custom integration
- YAML dashboards only
- stateless Streamable HTTP transport first
- typed card helpers only
- RFC 6902 JSON Patch for dashboard patch operations
