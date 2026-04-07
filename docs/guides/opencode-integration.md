# OpenCode Integration

## Prerequisites

- OpenCode installed
- This integration installed in Home Assistant
- A reachable Home Assistant base URL, for example `https://ha.example.com`
- A Home Assistant long-lived access token

## Current Connection Model

- MCP endpoint: `/api/homeassistant_mcp`
- Transport: `streamable_http_stateless`
- Authentication: standard Home Assistant bearer token
- OpenCode setting: `oauth: false`

## Create A Home Assistant Token

1. Open Home Assistant.
2. Go to **Profile**.
3. Under **Security**, create a **Long-lived access token**.
4. Store the token securely.

## Configure OpenCode

OpenCode supports remote MCP servers in `opencode.json`.

Example:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "homeassistant_mcp": {
      "type": "remote",
      "url": "https://ha.example.com/api/homeassistant_mcp",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:HOMEASSISTANT_TOKEN}"
      },
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

Recommended:

- use `https`
- keep `oauth: false` for the current token-based setup
- inject the token via environment variable instead of hardcoding it
- use a slightly higher timeout than the default if your Home Assistant host is slower

## Export The Token

Example shell setup:

```bash
export HOMEASSISTANT_TOKEN="your-long-lived-access-token"
```

## Verify The MCP Server In OpenCode

List configured MCP servers:

```bash
opencode mcp list
```

Then start OpenCode in your project:

```bash
opencode
```

Expected runtime behavior:

- the MCP server should appear in `opencode mcp list`
- an unauthenticated direct HTTP request returns `401 Unauthorized`
- an authenticated MCP `initialize` request returns `Home Assistant MCP`
- `tools/list` returns the stable `lovelace.*` and `hass.*` tool catalog
- `resources/list` and `prompts/list` currently return empty lists until later phases add built-in definitions
- `completion/complete` returns built-in suggestions for `entity_id`, `dashboard_id`, `view_id`, `card_id`, and `icon`

## Completion Context

The completion endpoint can use the current tool arguments as context. For dependent identifiers:

- pass `ref.arguments.dashboard_id` when completing `view_id`
- pass `ref.arguments.dashboard_id` and `ref.arguments.view_id` when completing `card_id`

## Example Prompts

Use the MCP server explicitly in prompts when helpful.

Example 1:

```text
Use homeassistant_mcp to list my YAML dashboards and summarize their current views.
```

Example 1b:

```text
Use homeassistant_mcp to list my Home Assistant entities in the kitchen and suggest which ones should appear on a Lovelace dashboard.
```

Example 2:

```text
Use homeassistant_mcp to create a dashboard called Energy with one Overview view and a tile card for sensor.grid_power.
```

Example 3:

```text
Use homeassistant_mcp to patch the dashboard main and rename the first view to Living Room.
```

Example 4:

```text
Use homeassistant_mcp completion support to suggest the right `entity_id` and `icon` values while creating a new tile card.
```

## Example AGENTS.md Rule

You can guide OpenCode to use this MCP server when working on Home Assistant prompts.

```md
When the task is about Home Assistant Lovelace dashboards, use `homeassistant_mcp`.
Prefer typed dashboard, view, and card operations over ad-hoc edits.
```

## Troubleshooting

- `401 Unauthorized`: the token is missing, invalid, or expired
- `404 Not Found`: the integration is not loaded, or the base URL or endpoint is wrong
- `405 Method Not Allowed`: the endpoint is loaded, but the request used `GET` instead of `POST`
- timeout: increase the MCP timeout in `opencode.json`
- no tools available: verify the server is enabled and reachable with `opencode mcp list`
