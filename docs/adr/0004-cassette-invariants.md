# 0004 Cassette evals check invariants

## Status

Accepted. 2026-10-18.

## Context

Exact tool-call transcripts break when a prompt is reworded, and they do not tell you whether money moved. CI must not call a paid API.

## Decision

Cases live in `evals/cases.json` and carry a frozen plan (the cassette). The runner executes the real runtime. Checks in `src/a2a_gate/evalkit/checks.py` score the finished task, the chain, and the logs. `eval-regression` runs one credit-note case with the gate disabled and must fail `risky effect without approval`. The command exits 1. CI treats that exit as success of the proof.

The cassette shape is adapted from the public repo agent-runtime-evals. See `docs/PROVENANCE.md`.

## Consequences

A green gate means the invariants held, not that the planner said a particular sentence. Token counts in the case files are simulated. A real model is not in this gate.
