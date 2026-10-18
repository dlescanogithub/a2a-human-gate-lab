# a2a-human-gate-lab

A local lab that tests one thing: an A2A-style back-office agent may propose a risky action, and the action does not hit the ledger unless a second person allows it. The model is a fake planner. The company, Nube Austral, is fictional. This is not a production system and it has not been used with a real client.

## Problem and result

A back-office model can fill in a credit note or a supplier bank change and sound sure of itself. The expensive mistakes are the ones that leave the building: the wrong amount, the wrong account, a second copy of an action that was already rejected. The lab puts the decision in ordinary code. The planner proposes. A policy chooses auto, needs-approval, or forbidden. A different person approves. A hash-chained log records the decision. A kill switch stops later effects.

Measured on 2026-10-18, package 0.1.0, Python 3.12.3: the cassette gate passed **37 of 37** scripted cases. Command: `.venv/bin/python -m a2a_gate.evalkit run` (exit 0, `elapsed_ms` 24 for that one local run). The forced regression, `.venv/bin/python -m a2a_gate.evalkit regression`, exited 1 and printed `invariant: risky effect without approval`. Pytest the same day: 19 passed, coverage 89.42% (`pytest` 9.1.1, `.venv/bin/pytest --cov=a2a_gate --cov-report=term-missing --cov-fail-under=80`). Pytest also printed `CoverageWarning: Module a2a_gate was previously imported, but not measured`; the 89.42% figure is the total pytest-cov printed anyway.

## Demo

```bash
python -m a2a_gate demo
```

`make demo` is the same command. The process generates throwaway tokens, labels them NOT REAL, and does not store them. No network and no API key.

## Business case

A finance pilot with one action type, the credit note. The time saved, the errors avoided, and the cost per approved action below are **[EST]**. This repository does not measure them. The only measured software cost here is zero, because CI and the demo never call a paid model. Detail: [docs/BUSINESS_CASE.md](docs/BUSINESS_CASE.md).

## Architecture

```mermaid
flowchart LR
  client[Local client] --> http[LAB-HTTP task API]
  http --> planner[Fake or cassette planner]
  planner --> policy[Risk policy]
  policy -->|auto| ledger[Fake downstream ledger]
  policy -->|needs approval| queue[Approval queue]
  queue --> person[Second person]
  person -->|approve| ledger
  person -->|reject| closed[Rejected stays rejected]
  admin[Admin token from env] --> kill[Kill switch]
  kill --> ledger
  http --> evidence[Hash-chained JSONL]
  queue --> evidence
  ledger --> evidence
```

The planner never sets the amount, never chooses the idempotency key, and never approves itself. Credit-note amounts come from the synthetic ledger. More detail: [docs/architecture.md](docs/architecture.md).

## Results

Measured 2026-10-18, package 0.1.0, Python 3.12.3, on this workspace. One run each. Not a benchmark suite.

| Check | Command | Result |
|---|---|---|
| Unit and integration tests | `.venv/bin/pytest --cov=a2a_gate --cov-report=term-missing --cov-fail-under=80` | 19 passed, coverage 89.42% |
| Eval gate | `.venv/bin/python -m a2a_gate.evalkit run` | pass, 37/37, exit 0, elapsed_ms 24 |
| Forced regression | `.venv/bin/python -m a2a_gate.evalkit regression` | exit 1, `risky effect without approval` |
| Secret scan | `.venv/bin/python -m a2a_gate.secretscan` | `secret scan: no findings` |
| Demo | `.venv/bin/python -m a2a_gate demo --evidence /tmp/demo-evidence.jsonl` | 1 applied effect, kill blocked the next one, evidence `valid entries=26` |
| Local HTTP | `python -m a2a_gate serve` on 127.0.0.1:8765, then curl | health 200, self-approval 403, approve 200, replay same task, kill then credit note `blocked` |

Case mix in `evals/cases.json`: 12 happy, 12 edge, 13 adversarial. Invariants, not transcripts: no risky effect without approval, no self-approval, a rejection stays a rejection, nothing effectful after the kill switch, the hash chain verifies, and notes, emails, account numbers, and secret-shaped strings stay out of the log.

| Real model | Result |
|---|---|
| Measured with a real model | none yet |

Cassette token counts in the case files (24 in / 12 out) are **simulated**. The fake keyword planner records 0 tokens. No vendor invoice exists for this repo.

## Use cases, governance and business strategy

### Client-style use cases

Nube Austral is fictional. The rows are patterns, not a client engagement.

| Use case | Status | Problem | Who approves | Gated effects | How this repo handles it |
|---|---|---|---|---|---|
| Credit-note approval | Implemented | A duplicate or partial invoice should become a credit note only when the amount is allowed and, above a threshold, a second person agrees | `finance_approver` or `admin`, never the requester | `issue_credit_note` on the fake ledger | Policy in `src/a2a_gate/data/nube_austral.yaml`. Under 5000 cents auto, 5000 to 500000 needs approval, above 500000 forbidden, zero forbidden. Amount is the ledger amount |
| Supplier bank-account change | Implemented | A note, including a hostile note, tries to move a supplier payout account | Same second person | `change_supplier_bank` | Always needs approval. Adversarial cases cover injection, a compromised plan, and a replay after reject |
| Customer notice drafting | Design only | Someone wants a customer told about the credit note | A person, in a future channel | Send is not implemented | `draft_notice` writes a local draft and does not send. `send_customer_notice` is forbidden |
| Procurement exception | Design only | A buyer wants to skip a purchasing rule | A procurement owner, not built | None | The action name is forbidden. There is no procurement workflow |

### Personal use cases

| Use case | Status | Problem | Who approves | Gated effects | How this repo handles it |
|---|---|---|---|---|---|
| Personal expense approvals via phone | Design only | A shared household wants a second yes before money moves | The other person, on a phone | A payment, which this lab does not send | Not built. The same shape would be a pending task plus a second actor. No phone channel exists |
| Family shared-calendar actions | Design only | An assistant proposes a calendar change that other people should accept | Another family member | A calendar write | Not built. No calendar tool exists |

### Design-only vs implemented

| Piece | Status |
|---|---|
| Agent card, task create/get/cancel, states, approval, reject, idempotency, hash chain, kill switch, fake planner, cassette evals | Implemented, local only |
| Real IdP / OIDC | Design only |
| Multi-tenant | Design only |
| Email or Slack approvals | Design only |
| Signed agent cards | Design only |
| A2A streaming and push notifications | Design only |
| Hosting | Design only |
| Real LLM calls | Adapter exists, off by default, not run, none measured |
| Sending a customer notice, procurement exceptions, phone expenses, family calendar | Design only |

### Governance

| Control | Where it lives |
|---|---|
| Risk policy, thresholds, approver roles, TTL | `src/a2a_gate/data/nube_austral.yaml`, loaded by `src/a2a_gate/policy.py` |
| Human approval and separation of duties | `src/a2a_gate/runtime.py` (`approve`, `reject`). The requester id cannot decide |
| Traceability | `src/a2a_gate/evidence.py`. Check with `python -m a2a_gate verify-evidence PATH` |
| Risks | [docs/RISKS.md](docs/RISKS.md) |
| Costs | [docs/COST.md](docs/COST.md) |
| Incident and rollback | [docs/RUNBOOK.md](docs/RUNBOOK.md) |
| What the eval refuses to ship | `evals/rubric.json`, `src/a2a_gate/evalkit/checks.py` |
| CI | `.github/workflows/ci.yml` |

Not covered yet: real login, tenant isolation, a notification channel, signed cards, streaming, a hosted process, a real ledger, a measured model, and branch protection (that is a GitHub setting, not a file in this repo).

### Business strategy

The business problem is a back office that wants a model to prepare credit notes without letting the model pay them. The ROI model is **[EST]** and lives in [docs/BUSINESS_CASE.md](docs/BUSINESS_CASE.md). Scope and phases are in [docs/SCOPE.md](docs/SCOPE.md). Success metrics are in [docs/METRICS.md](docs/METRICS.md). This lab is phase 0: one fictional company, one implemented money action, offline.

Deployment Strategist conversation: start with discovery, not with a model name. Who may approve, what the thresholds are, which system owns the amount, and what "undo" means. Then run shadow: the agent proposes, a person still types the real entry, and you compare. Only after the invariants hold do you let the gate release one action type into a ledger. Finance owns the policy and the approvals. The platform owner owns the log, the kill switch, and the rollback. The model owner does not own the effect.

## Decisions

- [0001 Simplified local HTTP, not a conformance claim](docs/adr/0001-simplified-local-http.md)
- [0002 Human gate and separation of duties](docs/adr/0002-human-gate-and-separation-of-duties.md)
- [0003 Hash-chained evidence and an allowlist](docs/adr/0003-hash-chained-evidence.md)
- [0004 Cassette evals check invariants](docs/adr/0004-cassette-invariants.md)
- [0005 Idempotency, bounded retries, dead letter](docs/adr/0005-idempotency-retries-dead-letter.md)
- [0006 Kill switch credential comes from the environment](docs/adr/0006-kill-switch-from-env.md)
- [0007 The ledger amount, not the model, is the amount](docs/adr/0007-ledger-amount.md)

## Security and known limits

Secrets are environment variables. Names and empty placeholders are in `.env.example`. The demo generates tokens in memory and prints that they are NOT REAL. CI does not set `LIVE_MODE` or an API key.

### What this does NOT do

- It does not call a paid model, and it has no measured run against one.
- It does not host anything. The card URL is a placeholder (`PUBLIC_BASE_URL`, default `http://127.0.0.1:8765`).
- It does not sign the agent card.
- It does not speak official A2A JSON-RPC, gRPC, or the official HTTP+JSON binding. It does not stream and it does not push.
- It does not authenticate people. `API_TOKEN` is a lab bearer. It is not an IdP.
- It does not send email, Slack, or payments.
- It does not stop a person who can edit the evidence file or the process memory. The chain detects tampering after the fact. It does not prevent it.
- It does not prove a production control. The regression fails because the test harness turns the gate off. The server and the demo cannot turn the gate off.

More: [SECURITY.md](SECURITY.md), [docs/RISKS.md](docs/RISKS.md).

## How to reproduce

Cost by default: **zero**. No key, no network in tests, no paid API.

`make` is optional. The commands below use the venv directly.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
.venv/bin/python -m pytest --cov=a2a_gate --cov-report=term-missing --cov-fail-under=80
.venv/bin/python -m a2a_gate.evalkit run
.venv/bin/python -m a2a_gate.evalkit regression   # must exit 1
.venv/bin/python -m a2a_gate.secretscan
.venv/bin/python -m a2a_gate demo
.venv/bin/python -m a2a_gate verify-evidence var/demo-evidence.jsonl
```

To serve locally, export `API_TOKEN` and `ADMIN_TOKEN` yourself. Do not commit them. Bind stays on `127.0.0.1` unless you change `A2A_HOST`.

```bash
export API_TOKEN="replace-me"
export ADMIN_TOKEN="replace-me"
.venv/bin/python -m a2a_gate serve
```

`make setup`, `make lint`, `make test`, `make eval`, `make eval-regression`, and `make demo` call the same tools.

## Next steps

1. Keep the gate on for any new effectful action. Add the invariant first, then the action.
2. If a real model is ever measured, record the provider, model, date, command, and a public price URL. Until then the table stays "none yet".
3. A real pilot would still need an IdP, a system of record, and a person who owns the kill switch. Those are design-only here.
4. Branch protection on `main` is a repository setting. This repo does not turn it on.

## Where to go next in the docs

- [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) — walkthrough in plain Spanish
- [docs/architecture.md](docs/architecture.md)
- [docs/BUSINESS_CASE.md](docs/BUSINESS_CASE.md)
- [docs/DISCOVERY.md](docs/DISCOVERY.md)
- [docs/SCOPE.md](docs/SCOPE.md)
- [docs/RISKS.md](docs/RISKS.md)
- [docs/METRICS.md](docs/METRICS.md)
- [docs/COST.md](docs/COST.md)
- [docs/RUNBOOK.md](docs/RUNBOOK.md)
- [docs/ADAPT_TO_A_REAL_CLIENT.md](docs/ADAPT_TO_A_REAL_CLIENT.md)
- [docs/PROVENANCE.md](docs/PROVENANCE.md)
- [SECURITY.md](SECURITY.md)
- [CHANGELOG.md](CHANGELOG.md)
