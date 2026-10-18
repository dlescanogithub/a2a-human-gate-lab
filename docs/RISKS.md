# Risks

Owners are roles. They are not real people. Probability and impact are labels for a conversation, not a measured frequency.

| Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Model skips approval or says it was already approved | Expected in adversarial cases | High if the gate trusted it | Policy ignores claims. Invariant `risky effect without approval`. Measured by the cassette set on 2026-10-18 | Platform owner |
| Requester approves their own note | Expected | High | Compare actor id to requester id before role. 403 `self_approval` | Finance owner |
| Rejection is replayed until it posts | Expected | High | Terminal `rejected` returns the same task. No second effect | Finance owner |
| Note text is treated as an instruction | Expected | High | Fake planner reads the user message only. Compromised cassette still waits for approval. Injection string is absent from the log | Platform owner |
| Amount in the prompt understates the ledger | Expected | High | Credit amount is `Record.amount_cents` | Finance owner |
| Kill switch unknown or token in the repo | Possible if someone hard-codes it | High | Token from `ADMIN_TOKEN` only. Empty token never matches. Demo generates a token and does not print it | Platform owner |
| Evidence file edited | Possible for anyone with the disk | High for audit, the effect already happened | `verify-evidence` fails the chain. It does not roll back | Platform owner |
| PII in logs | Possible if a new field is logged | Medium | Allowlist in `evidence.py`. Evals scan for emails, account numbers, notes, and `sk-` | Platform owner |
| Downstream double-post | Possible on retries | High | Idempotency key, replay returns the stored result, bounded attempts then dead letter | Platform owner |
| Queue expires and nobody notices | Possible | Medium | TTL 3600s in the lab YAML. Runbook "approval queue stuck" | Finance owner |
| Someone treats this repo as production | Possible | High | README states it is a lab. No hosting, no real model measurement | Deployment strategist |
| Paid API called from CI | Low if the workflow stays as written | Medium | `LIVE_MODE` unset. Tests do not open a vendor socket. Live adapter raises `live_off` | Platform owner |

Not covered: a real attacker with a shell on the host, a malicious dependency, or a stolen cloud token. Those need controls this repo does not implement.
