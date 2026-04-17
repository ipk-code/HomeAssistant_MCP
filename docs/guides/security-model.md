# Security Model

## Principles

- Validate all client input.
- Reject unknown fields rather than silently accepting them.
- Do not execute or deserialize untrusted code.
- Avoid direct file path input from clients.
- Minimize privilege and surface area for mutations.
- Return controlled error messages to clients.
- Write files atomically to prevent partial state corruption.
- Keep prompts, resources, and completions advisory or read-only.
- Default to least privilege: admin functions are disabled until explicitly enabled.

## Admin Function Toggle

Admin-only MCP tools are disabled by default (`enable_admin_functions = false`). The Home Assistant integration owner must explicitly enable the toggle in the integration setup or options flow. When disabled:

- Admin-gated tools are hidden from `tools/list`.
- Direct calls to disabled admin tools return a controlled MCP error.
- Changing the toggle reloads the integration immediately via `OptionsFlowWithReload`.

Current admin-gated tools: `hass.create_lovelace_dashboard`, `hass.update_lovelace_dashboard_metadata`, `hass.save_lovelace_dashboard_config`, `hass.delete_lovelace_dashboard`, `hass.list_template_sensors`, `hass.get_template_sensor`, `hass.preview_template_sensor`, `hass.create_template_sensor`, `hass.update_template_sensor`, `hass.delete_template_sensor`.

## Input Validation Controls

- **CWE-20 (Improper Input Validation):** Identifier formats are constrained by regex validation.
- **CWE-20 (NaN/Infinity rejection):** `ensure_number()` in `lovelace/validation.py` rejects `NaN`, `Infinity`, and `-Infinity` so persisted documents stay JSON-safe.
- **CWE-20 (Template sensor sanitization):** `TemplateSensorProvider._sanitize_json()` converts non-finite floats to `None` before they reach MCP responses.
- **CWE-601 (Open Redirect):** URL validation rejects `javascript:`, `data:`, `vbscript:`, and protocol-relative (`//example.com`) URLs.
- **Unknown fields:** The API rejects unknown input fields rather than silently passing them through.
- **Schema validation:** MCP tool arguments are validated against the published v1 schema before dispatch.

## Resource Exhaustion Controls (CWE-400)

- HTTP request bodies are size-limited; oversized requests are rejected before reading the body when `Content-Length` already exceeds the server limit.
- Card nesting depth is capped to prevent deeply recursive structures.
- JSON Patch operations are capped per request.
- Views per dashboard and cards per view are bounded.
- Discovery results, completion suggestions, and prompt summaries are bounded by configurable limits.

## Output Serialization Controls

- **CWE-20 (allow_nan=False):** All wire-protocol `json.dumps` calls in `transport.py` and `resources.py` use `allow_nan=False` so non-finite floats cause a serialization error rather than producing non-standard JSON tokens.
- **JSON Patch scope:** JSON Patch is limited to `/metadata` and `/views` paths and cannot mutate immutable identity fields.
- **Mutation calls** support `expected_version` for optimistic concurrency.
- **Error responses:** Unexpected transport exceptions return a generic internal error without leaking implementation details.

## Log Injection Controls (CWE-117)

- All user-controlled values are sanitized through the `_s()` helper before being written into MCP transport logs.
- All ASCII control characters (not just CR/LF) are escaped using hex escapes to prevent log injection and log forging.

## Identity and Randomness Controls

- **CWE-330 (Insufficient Randomness):** Generated card IDs use `uuid4`-based identifiers instead of process-local counters to avoid collisions across restarts.

## File System Controls (CWE-732)

- The API does not accept client-provided file system paths.
- Owner-only permissions are applied to managed dashboard storage directories on supported filesystems.
- Repository writes are atomic to reduce the risk of partial state corruption.

## Native Lovelace Dashboard Protection

- Native Home Assistant Lovelace dashboard access stays read-only and separate from MCP-managed dashboard mutations.
- Native dashboard writes are limited to storage dashboards; the default, YAML, and auto-generated dashboard variants are rejected.
- Native dashboard reads respect `require_admin` so non-admin MCP callers do not learn about protected dashboards.

## Template Sensor Admin Gating

- All template sensor tools require an admin-authenticated Home Assistant user at both the transport layer (`_ensure_tool_enabled`) and the provider layer (`_require_admin`).
- Template sensor preview results are sanitized for non-finite floats before serialization.

## JSON Patch Constraints

- JSON Patch is restricted to `/metadata` and `/views` target paths.
- Identity fields (`id`, `dashboard_id`) cannot be mutated through patch operations.
- The number of patch operations per request is bounded.

## Built-in Resources and Prompts

- Built-in resources expose only Home Assistant context and managed dashboards.
- Built-in prompts guide clients toward existing typed tools and resources instead of hidden operations.
- Frontend panel config payloads are sanitized to avoid surfacing obvious secret-like keys.
- Lovelace resource URLs are sanitized to strip obvious secret-like query parameters.

## Review Checklist

- Is user input validated for type, length, and allowed keys?
- Can any mutation escape the intended dashboard document scope?
- Can any read-only capability expose more entities, dashboards, or prompt context than intended?
- Can a failed write leave corrupted state behind?
- Does an error leak implementation details or internal paths?
- Do tests cover both valid and malicious inputs?
- Are non-finite floats rejected at both input validation and output serialization boundaries?
- Are user-controlled values sanitized before logging?
- Is admin gating enforced at both the transport and provider layers?
- Are new tools added to the `ADMIN_REQUIRED_TOOLS` set if they perform mutations or expose sensitive data?
