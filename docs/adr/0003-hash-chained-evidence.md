# 0003 Hash-chained evidence and an allowlist

## Status

Accepted. 2026-10-18.

## Context

A later reader has to see who approved what, and a tampered file should fail a check. Customer notes in this lab are synthetic and still do not belong in the log. One of them is a prompt injection.

## Decision

Append JSONL. Each line stores the previous hash and a new sha256 over the canonical body. `verify` recomputes the chain. `append` writes only an allowlist of fields (ids, amounts, roles, reason codes, token counts). Unknown keys such as a note are dropped.

## Consequences

Tamper detection is after the fact. Anyone who can rewrite the file and the hashes together can lie. The unit test mutates a copy and expects `verify` to fail. Operational response is in the runbook, not in an automatic repair.
