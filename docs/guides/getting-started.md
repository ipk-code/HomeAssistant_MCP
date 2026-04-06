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

## Current Development Focus

1. Expand Home Assistant integration behavior beyond the current stateless endpoint.
2. Add more integration-level tests around Home Assistant views and runtime wiring.
3. Keep YAML dashboard mutations secure and deterministic.

## Notes

The repository now renders true YAML for managed Lovelace dashboard output files.
