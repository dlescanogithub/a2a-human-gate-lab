# Metrics

Two kinds of numbers. Do not mix them.

## Measured in this lab

Date 2026-10-18. Package 0.1.0. Python 3.12.3.

| Metric | Value | Command |
|---|---|---|
| Eval cases passed | 37/37 | `.venv/bin/python -m a2a_gate.evalkit run` |
| Eval elapsed, one run | 24 ms for the whole suite | same command, field `elapsed_ms` |
| Forced regression | exit 1 | `.venv/bin/python -m a2a_gate.evalkit regression` |
| Tests | 19 passed | `.venv/bin/pytest --cov=a2a_gate --cov-report=term-missing --cov-fail-under=80` |
| Coverage | 89.42% | same pytest command. A CoverageWarning was also printed; see the README |
| Demo applied effects | 1, then 0 new after kill | `.venv/bin/python -m a2a_gate demo --evidence /tmp/demo-evidence.jsonl` |
| Evidence after that demo | `valid entries=26` | `.venv/bin/python -m a2a_gate verify-evidence /tmp/demo-evidence.jsonl` |
| Real-model quality | none yet | no command was run |

The 24 ms figure is one local run of 37 in-process cases. It is not a p50 or p95 of a service.

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
