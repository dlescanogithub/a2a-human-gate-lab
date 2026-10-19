# Runbook

This operates the lab process, not a hosted service. There is no pager. Roles are Finance owner, Platform owner, and the person on call for the lab, which may be the same human while it is a portfolio project.

## Operate

1. Install with `python3 -m venv .venv` and `.venv/bin/python -m pip install -e ".[dev]"`.
2. Demo: `.venv/bin/python -m a2a_gate demo`. It does not need tokens.
3. Serve: set `API_TOKEN` and `ADMIN_TOKEN` in the environment. Bind `A2A_HOST=127.0.0.1`. Command: `.venv/bin/python -m a2a_gate serve`.
4. Watch logs on stderr. They are JSON. They should contain task ids and reason codes, not emails or notes.

## Monitor

- Pending tasks are those whose `status.state` is `input-required`.
- `GET /v1/evidence/verify` with the bearer token returns `ok`.
- A dead letter is `effect_status: dead_letter` and task state `failed`. The fake ledger did not apply it.
- There is no metrics endpoint. Counting lines in the evidence file is the lab monitor.

## Approval queue stuck

Symptom: tasks stay `input-required` and nobody approves.

1. Read `expiresAt` on the action. The lab TTL is 3600 seconds from the policy file.
2. Confirm the approver is not the requester. A 403 `self_approval` is the control working.
3. If the approver role is wrong, the 403 is `wrong_role`. Fix the role, do not weaken the check.
4. If the TTL has passed, an approve call moves the task to `rejected` with reason `approval-expired`. That is final. A new business event needs a new idempotency key.
5. There is no email or Slack nudge. That channel is design-only. The stuck queue is visible only to whoever calls `GET /v1/tasks/{id}`.

## Kill switch drill

Do this against the local process, never against a system this repo does not run.

1. Start `serve` with an `ADMIN_TOKEN` that is not in git.
2. Create a credit note that would otherwise auto-apply (`INV-1002` in the catalog, 4000 cents) or approve one that is waiting.
3. `POST /v1/admin/kill-switch` with `Authorization: Bearer` and `X-Admin-Token`, body `{"actor_id":"admin.ops","actor_role":"admin"}`.
4. Expect `{"killed": true}` and a `kill_switch` line in the evidence file.
5. Create another effectful task. Expect state `failed`, reason `kill-switch`, `effectStatus` `blocked`.
6. A wrong token returns 403 `admin_token` and does not flip the switch.
7. The drill does not clear the switch. Restart the process. The lab switch is in memory.
8. Effects applied before the switch stay applied. Rollback is a reversing entry, which this fake ledger does not post. Say that out loud in the drill.

Measured once on 2026-10-18 with curl against `127.0.0.1:8765`: after kill, a 4000-cent credit note returned `effectStatus` `blocked` and reason `kill_switch`. That was a manual check in this workspace, not a scheduled drill.

## Evidence chain verification failed

Symptom: `python -m a2a_gate verify-evidence PATH` prints `hash mismatch` or `prev mismatch` and exits 1.

1. Stop treating the file as proof. Do not delete it.
2. Copy the file aside. The log is append-only; do not rewrite it to "fix" the hash.
3. Find the first bad line number in the message.
4. Decide whether the edit was a drill (the unit test tampers a copy) or an unexpected write.
5. New events belong in a new file only after a person records why the old chain stopped. The lab does not automate that decision.
6. A failed chain does not by itself roll back the ledger. Check `applied` keys separately.

## Ownership

| Thing | Role |
|---|---|
| Thresholds and who may approve | Finance owner |
| Evidence file, kill switch token, process | Platform owner |
| Whether a posted note is reversed | Finance owner, outside this process |
| Turning on the live planner | Whoever holds `XAI_API_KEY`, outside CI. Default off. The 2026-10-18 note is the README section "Live measurement (xAI)" |

## Live planner (opt-in)

This calls xAI. Do it on a machine you control, with a key that is not in the repo.

1. Export `LIVE_ENABLED=1` and `XAI_API_KEY`. The command reads the key from the environment. Do not put it in a file, a cassette, a log, or a report.
2. Leave `MAX_LIVE_SPEND_USD` at `0.10` unless you have a reason to raise it. The client checks the cap before it sends the next request, including before a retry. A response's `usage.cost_in_usd_ticks` is the cost when that field is present. Otherwise it uses the dated fallback rates in `.env.example`, marked [EST].
3. Run `make eval-live` or `.venv/bin/python -m a2a_gate.evalkit live --out var/live/run`. `var/` is gitignored. The JSONL log records HTTP status, latency, tokens, cached tokens, cost, and the case id. On the successful attempt it also records `proposed_action_names` (action names only) and `action_results` (`action`, `result` of `accepted`, `rejected`, `input-required`, or `executed`, and `reason_code` when rejected). A name that is not a short token is stored as `redacted_name`. The summary prints `proposals_by_action`, `proposals_rejected`, `proposals_approval_requested`, and `proposals_unknown_or_out_of_policy`. It does not record the prompt, the note, record ids, amounts, emails, or the key. The 2026-10-18 files in `docs/live/` were measured before these fields existed.
4. Only the planner is live. Approvals stay the scripted decisions in `evals/cases.json`. Do not point this command at a real ledger, and do not treat a green invariant line as a proof.
5. Do not run it from CI. Do not set `LIVE_ENABLED` in the workflow. `pytest` must keep using the fake transport.
6. If the command prints `live: disabled` or `XAI_API_KEY is empty`, it has not opened a socket. If it prints `aborted: live_spend_cap`, it stopped before the next request. Leave the partial `calls.jsonl` in `var/` and do not commit it.
7. Optional env: `XAI_BASE_URL`, `XAI_MODEL` (default `grok-4.20-0309-non-reasoning`), `XAI_MAX_ATTEMPTS` (default 3, only 429 and 5xx), `XAI_TIMEOUT_S` (default 60).

## Handoff

Give the next person this repo, `.env.example`, and the runbook. Do not give them a filled `.env`. Tell them the demo token is generated and discarded. Tell them `eval-regression` is supposed to fail.

## Rollback

- Not yet applied: cancel the pending task, or let it expire, or reject it.
- Kill switch: stops later effects. Restart to clear.
- Already applied: this fake ledger has no reversing entry. A real rollback is design-only and belongs to the system of record.
