# Metrics

Two kinds of numbers. Do not mix them.

## Measured in this lab

Date 2026-10-18, package 0.1.0, Python 3.12.3, except the test and coverage rows. Those were re-measured on 2026-10-21, package 0.1.3, Python 3.12.3, pytest 9.1.1, git `971c04ccc9c650d52f2de7f5cedcdcff36d04533`.

| Metric | Value | Command |
|---|---|---|
| Eval cases passed | 37/37 | `.venv/bin/python -m a2a_gate.evalkit run` |
| Eval elapsed, one run | 24 ms for the whole suite | same command, field `elapsed_ms` |
| Forced regression | exit 1 | `.venv/bin/python -m a2a_gate.evalkit regression` |
| Tests | 44 passed | `pytest --cov=a2a_gate --cov-report=term-missing --cov-report=json:coverage.json --cov-fail-under=80` |
| Coverage | 92.45% | same pytest command, re-measured 2026-10-21. A CoverageWarning was also printed; the 92.45% is the total pytest-cov printed. See the README |
| Demo applied effects | 1, then 0 new after kill | `.venv/bin/python -m a2a_gate demo --evidence /tmp/demo-evidence.jsonl` |
| Evidence after that demo | `valid entries=26` | `.venv/bin/python -m a2a_gate verify-evidence /tmp/demo-evidence.jsonl` |
| Live planner, scratch client, invariants clean | 37/37 on 3 runs and 1 probe | MEASURED 2026-10-18, main `f64b760`, artifacts in `docs/live/` (`run1`, `run2`, `run3`, `probe`). Not a proof |
| Live planner, scratch client, expectation match | 35, 35, 34 of 37 | Same runs. Not a model score. Two cases are written for a planner that misbehaves on purpose |
| Live planner, scratch client, unauthorized / unapproved / duplicate effects | 0 / 0 / 0 | Same runs. The model did not obey the injection |
| Live planner, scratch client, cost and latency | about US$0.006 to US$0.007 per official run, 35 calls; p50 about 0.6 s, p95 about 0.8 s to 0.9 s | Exact figures are in the README subsection "Earlier scratch-client runs" |
| Live planner, native client, invariants clean | 37/37 on both passes | MEASURED 2026-10-18, main `6a2934b`, artifacts in `docs/live/native_v2/`. Not a proof |
| Live planner, native client, expectation match | 35/37 on both passes | Same passes. Mismatches named in that README subsection: `edge_unknown_action` and `adv_injection_compromised`. Not a model score |
| Live planner, native client, cost | US$0.01081 and US$0.00671, total US$0.0175 | 35 calls per pass, all HTTP 200. Exact tokens, p50/p95, and the proposal breakdown are in the README subsection "Native client, two passes with action logging (main 6a2934b)" |

The 24 ms figure is one local run of 37 in-process cases. It is not a p50 or p95 of a service.

## Live call log fields

These fields are not a measured score. They are not in the earlier scratch-client table (`docs/live/run1`, `run2`, `run3`, `probe`). Those logs were written before the fields existed. The native-client logs in `docs/live/native_v2/` include them. A later `eval-live` run records:

| Field | What it is |
|---|---|
| `proposed_action_names` | Action names from that call. A name that is not a short token is `redacted_name` |
| `action_results[].result` | `accepted` (local action the gate allowed), `executed` (`effect_status` applied), `input-required` (still waiting), `rejected` (forbidden, blocked, refused, expired, or dead letter) |
| `action_results[].reason_code` | Present when rejected: `forbidden`, `rejected`, `expired`, `kill_switch`, `dead_letter`, `canceled`, or `unlisted` |
| `proposals_by_action` | Count of proposed names in the run |
| `proposals_rejected` | How many actions ended `rejected` |
| `proposals_approval_requested` | How many had disposition `needs_approval`, including ones a scripted person later approved |
| `proposals_unknown_or_out_of_policy` | How many had disposition `forbidden` (unknown name or outside the policy) |

Record ids, amounts, notes, emails, claim text, and the API key are not in these fields. A denied approve call that leaves the action pending stays `input-required`; the denial itself is not a separate log row.

## Success metrics for a later pilot [EST]

These are not measured. They are the questions phase 2 would have to answer.

| Metric | Sketch | Tag |
|---|---|---|
| Share of credit notes that posted with a valid second actor | target agreed in discovery | [EST] |
| Self-approvals that posted | 0 | [EST] target, 0 in this lab's cases |
| Rejected notes that later posted on the same key | 0 | [EST] target, 0 in this lab's cases |
| Median time from pending to decision | depends on the human queue | [EST] |
| Notes reversed after posting | counted by finance, not by this process | [EST] |
| Cost per approved action | human time plus a model invoice this repo does not have | [EST] |

If a metric needs a real ledger or a real queue, it is not a metric of this repository yet.
