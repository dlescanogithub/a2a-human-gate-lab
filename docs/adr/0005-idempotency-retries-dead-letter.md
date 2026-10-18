# 0005 Idempotency, bounded retries, dead letter

## Status

Accepted. 2026-10-18.

## Context

Clients retry. A fake downstream can fail twice and then succeed. A third failure should not look like a success.

## Decision

The runtime builds the effect key. A repeated task key returns the original task. A repeated effect key does not call the ledger again. Downstream calls use `retry_delay_s` from the vendored backoff helper, capped at 8 seconds, with `max_attempts` default 3. The sleeper is injected; tests pass a no-op. Exhausted attempts become `dead_letter` and the task is `failed`.

## Consequences

The lab can show a retry without waiting. A real ledger still needs the same key on its side. Dead letter does not page anyone.
