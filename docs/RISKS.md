# Risks

Owners are roles. They are not real people. Probability and impact are labels for a conversation, not a measured frequency.

| Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Model skips approval or says it was already approved | Expected in adversarial cases | High if the gate trusted it | Policy ignores claims. Invariant `risky effect without approval`. Measured by the cassette set on 2026-10-18 | Platform owner |
| Requester approves their own note | Expected | High | Compare actor id to requester id before role. 403 `self_approval` | Finance owner |
| Rejection is replayed until it posts | Expected | High | Terminal `rejected` returns the same task. No second effect | Finance owner |
| Note text is treated as an instruction | Expected | High | Fake planner reads the user message only. The live planner is told the note is data. On 2026-10-18 the measured model did not obey the injection. A compromised cassette still waits for approval. The injection string is absent from the evidence log | Platform owner |
| Amount in the prompt understates the ledger | Expected | High | Credit amount is `Record.amount_cents` | Finance owner |
| Kill switch unknown or token in the repo | Possible if someone hard-codes it | High | Token from `ADMIN_TOKEN` only. Empty token never matches. Demo generates a token and does not print it | Platform owner |
| Evidence file edited | Possible for anyone with the disk | High for audit, the effect already happened | `verify-evidence` fails the chain. It does not roll back | Platform owner |
| PII in logs | Possible if a new field is logged | Medium | Allowlist in `evidence.py`. Evals scan for emails, account numbers, notes, and `sk-` | Platform owner |
| Downstream double-post | Possible on retries | High | Idempotency key, replay returns the stored result, bounded attempts then dead letter | Platform owner |
| Queue expires and nobody notices | Possible | Medium | TTL 3600s in the lab YAML. Runbook "approval queue stuck" | Finance owner |
| Someone treats this repo as production | Possible | High | README states it is a lab. No hosting. The 2026-10-18 live run is a planner-only sample, not a production proof | Deployment strategist |
| Paid API called from CI | Low if the workflow stays as written | Medium | `LIVE_ENABLED` unset. `make eval-live` is not a CI step. Tests pass a fake transport and do not open a vendor socket | Platform owner |
| Live key or prompt written to a log or to git | Possible if a later change logs the request body | High | Key comes from `XAI_API_KEY` only. The call log refuses a line that contains the key. Tests check that the key, the prompt, and the note are absent. Do not commit `var/live/` | Platform owner |
| Live spend runs past a small bill | Possible if the cap is raised | Low at the default | `MAX_LIVE_SPEND_USD` defaults to 0.10 and is checked before the next request | Platform owner |

Not covered: a real attacker with a shell on the host, a malicious dependency, or a stolen cloud token. Those need controls this repo does not implement.
