# Security Model

## Principles

- Validate all client input.
- Reject unknown fields rather than silently accepting them.
- Do not execute or deserialize untrusted code.
- Avoid direct file path input from clients.
- Minimize privilege and surface area for mutations.
- Return controlled error messages to clients.
- Write files atomically to prevent partial state corruption.

## Current Controls

- Identifier formats are constrained by regex validation.
- Unsafe URLs such as `javascript:` are rejected.
- HTTP request bodies are size-limited.
- JSON Patch is limited to `/metadata` and `/views`.
- JSON Patch cannot mutate immutable identity fields.
- Mutation calls support `expected_version` for optimistic concurrency.
- Unexpected transport exceptions return a generic internal error.

## Review Checklist

- Is user input validated for type, length, and allowed keys?
- Can any mutation escape the intended dashboard document scope?
- Can a failed write leave corrupted state behind?
- Does an error leak implementation details or internal paths?
- Do tests cover both valid and malicious inputs?
