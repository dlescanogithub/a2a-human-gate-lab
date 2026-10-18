# 0006 Kill switch credential comes from the environment

## Status

Accepted. 2026-10-18.

## Context

An operator needs a way to stop new effects. A token in source control is not a control.

## Decision

`POST /v1/admin/kill-switch` requires the lab bearer plus `X-Admin-Token`. The expected value is `ADMIN_TOKEN`. Comparison hashes both sides and uses `hmac.compare_digest`. An empty expected token never matches. The actor role must be `admin`. The runtime writes a `kill_switch` evidence line, then blocks later effectful applies. `serve` refuses to start if `API_TOKEN` or `ADMIN_TOKEN` is empty. The demo generates both in memory, does not print them, and does not read a committed secret.

## Consequences

The switch is process memory. A restart clears it. Already applied effects stay applied. The drill is in `docs/RUNBOOK.md`.
