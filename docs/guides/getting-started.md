# Getting Started

## Repository Layout

- `custom_components/homeassistant_mcp/`: integration source
- `custom_components/homeassistant_mcp/lovelace_mcp_api_v1.json`: bundled v1 MCP tool contract
- `tests/`: unit tests
- `docs/`: repository documentation

## Local Test Command

```bash
python3 -m pytest tests -vv
```

## Real Home Assistant Test Setup

Install the test extras:

```bash
python3 -m pip install --break-system-packages ".[test]"
```

If your platform needs to build native wheels for Home Assistant test
dependencies, install a working C toolchain first.

Once a compiler is available, prefer the real compiled dependencies over local
compatibility shims when running the Home Assistant pytest suite.

Run the full pytest suite:

```bash
python3 -m pytest tests -vv
```

Run only the real Home Assistant integration tests:

```bash
python3 -m pytest tests/components/homeassistant_mcp -vv
```

## Current Development Focus

1. Keep the stable dashboard-first MCP surface documented and test-covered.
2. Preserve the read-only guarantees for discovery, resources, completions, and prompts.
3. Evaluate future SSE and optional OAuth work without weakening the current Home Assistant auth model.

## Notes

The repository now renders true YAML for managed Lovelace dashboard output files.
