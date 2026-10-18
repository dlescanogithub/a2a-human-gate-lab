# Cost

No paid call was made. Prices below are either measured as zero or marked [EST]. There is no vendor price URL because no official price was copied.

| Scenario | Model / provider | Tokens or units | Cost / run | p50 / p95 latency | Quality | Price date / source |
|---|---|---|---|---|---|---|
| Demo walkthrough | fake keyword planner | 0 tokens recorded | 0 | not a service latency; the walkthrough finished in the same second as the 2026-10-18 demo command | 1 credit applied, bank change rejected, next credit blocked after kill | measured 2026-10-18, command `.venv/bin/python -m a2a_gate demo --evidence /tmp/demo-evidence.jsonl` |
| Eval gate, 37 cases | cassette, plus one fake-planner case | cassette files say 24 in / 12 out (**simulated**). The fake-planner case records 0 | 0 | one suite run `elapsed_ms` 24. Not a p50/p95 | 37/37 invariants | measured 2026-10-18, `.venv/bin/python -m a2a_gate.evalkit run` |
| Forced regression | same runtime with the gate flag off in the harness only | simulated cassette tokens, not billed | 0 | not measured separately | invariant fired, exit 1 | measured 2026-10-18, `.venv/bin/python -m a2a_gate.evalkit regression` |
| Hosted chat model, planner only | xAI `grok-4.20-0309-non-reasoning` | 35 calls per run. Prompt tokens 13591 on every run. Completion tokens 738 / 686 / 672 (probe 712) | MEASURED US$0.00728, US$0.00620, US$0.00644 per official run (unrounded `cost_usd` 0.00727535, 0.00620455, 0.00643835). Probe US$0.01057 (`0.01057035`). Total including probe US$0.0305 | MEASURED p50 / p95: 0.63 s / 0.91 s, 0.62 s / 0.78 s, 0.61 s / 0.82 s. Probe 0.67 s / 0.84 s | Invariants 37/37 on all three runs and the probe. Expectation match 35, 35, 34 of 37. That match count is not a model score. See the README | 2026-10-18, cost from `usage.cost_in_usd_ticks`. No public price URL copied |

CI does not set `LIVE_ENABLED` or `XAI_API_KEY`. Pytest uses a fake HTTP transport. `make eval-live` is the only command that can open a socket, and only after that opt-in. The default cap in the repo is US$0.10. The 2026-10-18 measurement used a US$0.30 cap. When a response has no cost ticks, the client falls back to rates marked [EST] as of 2026-10-18 (`XAI_INPUT_USD_PER_MTOK` default 3.0, cached 0.75, output 15.0 per million tokens). Those defaults were not used for the measured rows above.

Human review time for a real pilot is [EST] in [BUSINESS_CASE.md](BUSINESS_CASE.md). It is not in the table above because this process does not pay a person.
