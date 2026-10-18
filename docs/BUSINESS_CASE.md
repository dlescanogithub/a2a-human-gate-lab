# Business case

Fictional company: Nube Austral. One pilot action: `issue_credit_note`. Nothing here is a client result. Figures marked [EST] are illustrative. The only measured cost is the lab cost, which is zero.

## The problem

Credit notes are prepared often and paid once. A model is good at drafting the reason. It is a bad place to store the rule "this amount may post" or "this person may approve their own request". The pilot asks the model to prepare the case and asks a second person to release it when the amount is above a threshold.

## What this lab already shows

Measured 2026-10-18, package 0.1.0, Python 3.12.3:

- 37 of 37 scripted cases passed: `.venv/bin/python -m a2a_gate.evalkit run`
- The gate can go red: `.venv/bin/python -m a2a_gate.evalkit regression` exited 1
- Demo applied exactly one credit note and blocked the next one after the kill switch

That is a control demonstration. It is not a before/after on a finance team.

## ROI model [EST]

| Input | Value | Tag |
|---|---|---|
| Pilot volume | 40 credit notes / week | [EST] |
| Minutes to prepare and check, without an agent | 20 | [EST] |
| Minutes if the agent prepares and a person only approves | 4 | [EST] |
| Minutes saved per note | 16 | [EST] |
| Hours saved per week | 10.7 | [EST], 40 × 16 / 60 |
| Wrong notes caught by a second person | 2 / month | [EST] |
| Average note size | not used as money | [EST], do not invent a currency |
| Software cost per run in this repo | 0 | measured, fake provider, 2026-10-18 |
| Cost per approved action, fully loaded | human minutes only | [EST] |

The hours are not a promise. If discovery says the person still re-checks every field, the 4 minutes is wrong and the design should not claim savings. If the threshold is "everything needs approval", the auto path in the YAML should be removed before anyone talks about speed.

## What would have to be true

- Finance owns the thresholds and the approver list.
- The amount comes from the system of record, as it does from the catalog here.
- Rejection is final unless a new business event creates a new idempotency key.
- Someone can hit the kill switch and can explain what already posted.

Until those are true, the honest status is phase 0 in [SCOPE.md](SCOPE.md).
