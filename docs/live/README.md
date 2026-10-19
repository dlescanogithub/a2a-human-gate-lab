# Live measurement artifacts

Two copied samples from 2026-10-18. Nothing here was regenerated for this commit. The call logs do not contain prompts, record notes, or an API key.

## Native client, two passes with action logging (main 6a2934b)

`native_v2/REPORT.md`, `native_v2/run1/`, and `native_v2/run2/` are two passes of `python -m a2a_gate.evalkit live`. Each run has `calls.jsonl` (HTTP status, latency, tokens, cached tokens, cost ticks, `proposed_action_names`, `action_results`), `results.json`, `summary.json`, and `cases/`. Figures are in the README subsection of the same name. Planner only. Approvals were scripted.

## Earlier scratch-client runs (main f64b760)

`REPORT.md`, `run1`, `run2`, `run3`, and `probe` are the scratch client that lived outside this repo. The numbers were not regenerated when the live command landed in the tree. See the README subsection "Earlier scratch-client runs".
