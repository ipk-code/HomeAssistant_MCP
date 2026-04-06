# Getting Started

## Repository Layout

- `custom_components/homeassistant_mcp/`: integration source
- `specs/`: static v1 MCP tool contract
- `tests/`: unit tests
- `docs/`: repository documentation

## Local Test Command

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Real Home Assistant Test Setup

Install the test extras:

```bash
python3 -m pip install --break-system-packages ".[test]"
```

If your platform needs to build native wheels for Home Assistant test
dependencies, install a working C toolchain first.

Run the full pytest suite:

```bash
python3 -m pytest tests -vv
```

Run only the real Home Assistant integration tests:

```bash
python3 -m pytest tests/components/homeassistant_mcp -vv
```

## Current Development Focus

1. Expand Home Assistant integration behavior beyond the current stateless endpoint.
2. Add more integration-level tests around Home Assistant views and runtime wiring.
3. Keep YAML dashboard mutations secure and deterministic.

## Notes

The repository now renders true YAML for managed Lovelace dashboard output files.
