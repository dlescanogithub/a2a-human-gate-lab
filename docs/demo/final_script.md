# Final script: a2a_human_gate_lab_demo_en.mp4

Voice: xAI TTS leo, speed 1.08. The spoken lines are English. Captions for those lines are in [a2a_human_gate_lab_demo_en.en.srt](a2a_human_gate_lab_demo_en.en.srt). The video file still carries the original Spanish soft subtitle track and was not re-encoded.

## A_hook (starts 0.80 s)

- An agent proposes a credit note, or a supplier bank change.
- Can it just do it? No: a policy decides, and a second person approves.

## B_walk (starts 10.23 s)

- The credit note waits: input-required. Self-approval: denied.
- A second person approves, and it completes.
- Replay the same request: no second effect.
- The bank change? A human rejects it, and it stays rejected.
- Then the kill switch: the next action fails.
- Applied effects: one.

## C1_log (starts 29.54 s)

- Every step goes into a hash-chained log.
- Here: the self-approval denied, then the effect applied once.

## C2_tamper (starts 38.08 s)

- Now I edit one amount after the fact.
- Verification fails, at that exact line.

## D_eval (starts 44.85 s)

- Offline, thirty-seven cases pass.
- Then I force a regression. The gate catches a risky effect without approval, and exits with one.

## E_live (starts 54.29 s)

- Then a real model, planner only.
- Three runs and a probe: invariants clean, thirty-seven of thirty-seven, every time.
- Expected outcomes matched thirty-five on run one. Strictly, thirty-four.

## F_caveat (starts 67.86 s)

- Caveats. Only the planner was measured. Approvals were scripted.
- One model, one prompt, three runs. A good sign, not a proof.

## G_close (starts 78.62 s)

- Next would be shadow mode. Everything past the lab is design only.
- Not covered: real login, tenants, a real ledger.
- ROI: E-S-T, about eleven hours a week. An estimate, not a promise.
