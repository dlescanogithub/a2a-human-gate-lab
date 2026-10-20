# Changelog

## Unreleased

## 0.1.3 - 2026-10-20

- Docs: narrated demo under `docs/demo/` (real local run, synthetic xAI TTS, English and Spanish subtitles, number trace).
- Docs: native-client live artifacts for two passes on main `6a2934b` under `docs/live/native_v2/`. The README keeps the earlier scratch-client table as its own sample.
- Docs: add a three-line README TL;DR under the title.

## 0.1.2 - 2026-10-19

- Live call logs now add `proposed_action_names` and `action_results` (accepted, rejected, input-required, executed, plus a rejection code when the gate has one). Older log fields stay. Names that are not short tokens are stored as `redacted_name`.
- A live run summary counts proposals by action, how many were rejected, how many asked for approval, and how many were unknown or outside policy. The 2026-10-18 measured table was recorded before this logging and is unchanged.

## 0.1.1 - 2026-10-18

- Optional live planner. It calls xAI chat completions only when `LIVE_ENABLED=1` and `XAI_API_KEY` are set (`make eval-live` or `python -m a2a_gate.evalkit live`). CI and pytest do not set those and do not open a socket.
- Spend cap `MAX_LIVE_SPEND_USD` (default 0.10) checked before each request. Cost uses `usage.cost_in_usd_ticks` when the response has it, otherwise a dated [EST] fallback.
- JSONL call log: HTTP status, latency, tokens, cached tokens, cost, case. No prompt, no record note, no API key.
- Only the planner is live. Policy, the approval gate, scripted decisions, the kill switch, the hash chain, idempotency, and the invariants are unchanged.
- MEASURED planner-only runs from 2026-10-18 (main `f64b760`, model `grok-4.20-0309-non-reasoning`) are in `docs/live/` and summarized in the README. Those numbers were produced by a scratch client outside the repo and were not re-run for this release.

## 0.1.0 - 2026-10-18

Initial lab.

- Local LAB-HTTP task API, agent card, and task states for the fictional company Nube Austral.
- Approval gate, separation of duties, expiry, hash-chained evidence, kill switch, idempotent effects, bounded retries, dead letter.
- 37 cassette cases and a forced regression that exits 1.
- Fake planner by default. Optional live adapter present and off. No measured hosted-model run in 0.1.0. The 2026-10-18 measurement is recorded in 0.1.1.

Known limits are in the README section "What this does NOT do".
