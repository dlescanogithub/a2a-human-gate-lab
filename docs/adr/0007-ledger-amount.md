# 0007 The ledger amount, not the model, is the amount

## Status

Accepted. 2026-10-18.

## Context

A cassette can claim a 600000-cent invoice is a 100-cent credit note. If the policy trusts the claim, the note auto-posts under the threshold.

## Decision

For `issue_credit_note`, classification uses the catalog record's `amount_cents`. Claims are stored only as a count (`ignored_claims`) in the evidence line. The values are not written.

## Consequences

The model can still choose the record id. It cannot talk the amount down. A wrong record id is a different bug, and a missing record fails the task before any effect.
