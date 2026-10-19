# Live measurement artifacts

These files are the 2026-10-18 measurement against `main` `f64b760`. They are copied here so the README can point at them. The numbers were not regenerated when the live command landed in the repo.

`REPORT.md` is the write-up from that day. `run1`, `run2`, and `run3` are the three official runs. `probe` is an earlier run on the same harness. Each directory has `calls.jsonl` (one JSON object per call: HTTP status, latency, tokens, cached tokens, cost ticks), `results.json`, and `summary.json`.

The call logs do not contain prompts, record notes, or an API key. The measurement client lived outside this repo. The command in the tree now is a rewrite of that client. See the README section "Live measurement (xAI)".
