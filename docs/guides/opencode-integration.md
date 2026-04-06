# OpenCode Integration

## Prerequisites

- OpenCode installed
- This integration installed in Home Assistant
- A reachable Home Assistant base URL, for example `https://ha.example.com`
- A Home Assistant long-lived access token

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

## Example Prompts

Use the MCP server explicitly in prompts when helpful.

Example 1:

```text
Use homeassistant_mcp to list my YAML dashboards and summarize their current views.
```

Example 2:

```text
Use homeassistant_mcp to create a dashboard called Energy with one Overview view and a tile card for sensor.grid_power.
```

Example 3:

```text
Use homeassistant_mcp to patch the dashboard main and rename the first view to Living Room.
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
- timeout: increase the MCP timeout in `opencode.json`
- no tools available: verify the server is enabled and reachable with `opencode mcp list`
