# Cost

No paid call was made. Prices below are either measured as zero or marked [EST]. There is no vendor price URL because no official price was copied.

| Scenario | Model / provider | Tokens or units | Cost / run | p50 / p95 latency | Quality | Price date / source |
|---|---|---|---|---|---|---|
| Demo walkthrough | fake keyword planner | 0 tokens recorded | 0 | not a service latency; the walkthrough finished in the same second as the 2026-10-18 demo command | 1 credit applied, bank change rejected, next credit blocked after kill | measured 2026-10-18, command `.venv/bin/python -m a2a_gate demo --evidence /tmp/demo-evidence.jsonl` |
| Eval gate, 37 cases | cassette, plus one fake-planner case | cassette files say 24 in / 12 out (**simulated**). The fake-planner case records 0 | 0 | one suite run `elapsed_ms` 24. Not a p50/p95 | 37/37 invariants | measured 2026-10-18, `.venv/bin/python -m a2a_gate.evalkit run` |
| Forced regression | same runtime with the gate flag off in the harness only | simulated cassette tokens, not billed | 0 | not measured separately | invariant fired, exit 1 | measured 2026-10-18, `.venv/bin/python -m a2a_gate.evalkit regression` |
| Hosted chat model | not run | — | [EST] | [EST] | Measured with a real model: none yet | no public price copied |

CI does not set `LIVE_MODE`, `LLM_API_KEY`, or `LLM_BASE_URL`. The optional adapter in `src/a2a_gate/live.py` raises `live_off` unless those are set, and even then this lab has not called it against a network.

Human review time for a real pilot is [EST] in [BUSINESS_CASE.md](BUSINESS_CASE.md). It is not in the table above because this process does not pay a person.
