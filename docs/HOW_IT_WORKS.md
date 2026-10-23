# How it works

This is a walkthrough for engineers and buyers. The lab is local. The company, Nube Austral, is fictional. The "model" is a fake planner. There is no real client behind it.

## The analogy

Treat the system as a **check that needs two signatures**. The first signature does not pay by itself.

The first person (the agent) can fill in the check: who it is for, what it is for, and the amount. That is cheap and reversible. The bank (the system around the model) does not hand over the money if the second signature is missing. The same person cannot sign twice. If the check was voided, it stays voided even when someone presents it again. And if the branch manager pulls down the shutter (the kill switch), the till stops paying, even when the check already has both signatures and has not gone out yet.

The model reasons. The system around it decides whether that touches the world.

## The path, step by step

1. A local client creates a task. It sends a message ("credit note") and the id of a synthetic record (`INV-1001`).
2. The task moves through `submitted` and `working`.
3. The planner proposes actions. The fake planner looks at words in the message (`read`, `draft`, `credit`, `bank`). It does not read the customer note as an order.
4. The policy classifies each action: auto, needs approval, or forbidden. The amount of a credit note comes from the record, not from the model's text.
5. Reading and drafting a notice run on their own. They do not touch the downstream ledger.
6. A small credit note (under 5000 cents of a fictional unit) runs on its own. From 5000 to 500000 it waits for another person. Above 500000, or at zero, it is rejected. Changing a supplier's bank always waits.
7. The task stays in `input-required` with reason `approval-pending`.
8. If the same person who requested it approves, the system responds 403 and applies nothing.
9. If someone with role `finance_approver` or `admin` approves, and the deadline has not passed, the effect enters the fake ledger once.
10. If they reject it, the task stays `rejected`. A replay returns that same task. There is no second effect.
11. Each line of the log includes the hash of the previous line. `verify-evidence` recomputes the chain.
12. An admin with the token from the environment can pull the shutter. After that, a new effect is not applied.

## What is measured

On 2026-10-18, with Python 3.12.3 and package 0.1.0, `python -m a2a_gate.evalkit run` passed 37 of 37 cases. The forced regression command exited with code 1. That is in the README, with the exact command. It is not a production number.

## Glossary

| Word | What it means here |
|---|---|
| Task | A unit of work with an id and a state. Inspired by A2A, not the full official schema |
| Planner | The component that proposes actions. By default it is fake |
| Cassette | A frozen plan. The eval replays it so it does not call a paid model |
| Policy | The YAML file that says auto, approval, or forbidden |
| Effect | A write on the fake ledger: a credit note or a bank change |
| Idempotency | The same key returns the same result and does not write twice |
| Evidence | A JSONL file that only appends lines and chains them by hash |
| Kill switch | An admin order that stops new effects |
| Invariant | A condition that has to be true at the end, whatever path the model took |

## Limits, plainly

- It does not speak the full A2A protocol. On 2026-10-18 the public spec was checked (link in `docs/architecture.md`). This lab uses a few state names and a card at `/.well-known/agent-card.json`. The binding is named `LAB-HTTP` on purpose, so it does not claim JSON-RPC or the official HTTP+JSON binding.
- It does not sign the card. There is no streaming and no push.
- There is no real login. The lab bearer is not an IdP.
- It does not send email and it does not pay.
- The kill switch does not undo what was already applied. It stops what comes next.
- The hash chain detects that someone edited the file. It does not stop someone with disk access from editing it.
- The cassette tokens (24 and 12) are simulated. On 2026-10-18 there was an xAI measurement of the planner only: the "Live measurement (xAI)" section of the README, with the logs in `docs/live/`. That does not run in CI. 37/37 clean invariants is a good sign, not a proof, and the expectation match is not a score of the model.
