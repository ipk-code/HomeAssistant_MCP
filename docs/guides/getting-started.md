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

1. Finish Home Assistant HTTP wiring for stateless transport.
2. Add integration-level tests around Home Assistant views.
3. Keep YAML dashboard mutations secure and deterministic.

## Notes

The repository currently renders dashboard output as JSON text into `.yaml` files because JSON is valid YAML and keeps the implementation dependency-free for now.
