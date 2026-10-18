# Scope

No fees. No statement of work. Phases are a way to talk about rollout, not a calendar.

## Assumptions

- One fictional company, one team of synthetic role ids (`requester.ana`, `approver.finance`, `admin.ops`).
- The ledger in this repo is in memory and dies with the process.
- The planner is fake unless someone later turns on `LIVE_MODE` outside CI. That has not been measured.
- Amounts are fictional cents.

## Phases

| Phase | What | Status here |
|---|---|---|
| 0. Lab | Local task API, policy, gate, evidence, kill switch, cassette evals | Implemented |
| 1. Shadow | Proposals are logged. A person still posts the note in the real ledger by hand | Design only |
| 2. One gated action | `issue_credit_note` may post after approval, against a real system of record | Design only |
| 3. Second action | Supplier bank changes, still with a second person | Implemented only against the fake ledger. A real bank file is design only |
| 4. Channels | Email or chat for the queue, IdP, hosting | Design only |

Exit criteria to leave phase 0:

- The eval gate is green on `main` and the forced regression is red in CI.
- A named person owns the policy file and another named role owns the kill switch.
- Discovery questions 5, 6, and 10 have answers that are not "the model will know".

This repository does not meet the second or third exit. It meets the first only as a local lab: CI is defined in `.github/workflows/ci.yml` and was not observed running on GitHub from this workspace.

## Out of scope

- Real identity providers, tenants, signed cards, streaming, push notifications.
- Sending customer notices, procurement exceptions, phone approvals, calendar writes.
- A measured hosted model.
- Reversing an effect that already applied.
- Any fee, rate card, or staffing estimate stated as a real price.
