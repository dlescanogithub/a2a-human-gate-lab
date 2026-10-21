# Value Realization Plan: adopting `a2a-human-gate-lab`

> **Important notice**
> - **Fictional client.** "Fictional mid-size insurer" is a company **invented** for this exercise. It does not represent any real client or employer. The fictional company in the repo is a different one, "Nube Austral", which is also invented.
> - **Inspired by the AWS Business Value Realization (BVR) framework**: a value-realization plan, KPIs with a threshold at each stage ("pit stops"), and client confirmation. **It is not an official AWS template** (the official value-realization plan template is not public) and **I do not hold the AWS BVR Competency**, which is awarded to AWS partner companies, not to individuals.
> - Tags:
>   - **[REPO]**: measured or configured in this repo, with the source.
>   - **[REPO-EST]**: a figure this repo itself marks as an illustrative [EST].
>   - **[SYN]**: a synthetic business assumption invented for this case.
> - Repository: https://github.com/dlescanogithub/a2a-human-gate-lab. The [REPO] figures below were checked against `971c04ccc9c650d52f2de7f5cedcdcff36d04533` (2026-10-19), package 0.1.3. Package 0.1.0 is the earlier README sample on `c006882e4c849d7de39ea6c9e2d7acdcb2721fd6`, not the package at `971c04c`.
> - Recorded README sample, 2026-10-18, commit `c006882e4c849d7de39ea6c9e2d7acdcb2721fd6`, package 0.1.0, Python 3.12.3 [REPO]:
>   - eval 37/37, exit 0 (`elapsed_ms` 24 for that one local run);
>   - forced regression exit 1 with `invariant: risky effect without approval`;
>   - secret scan with no findings;
>   - demo with `applied effects: 1` and `evidence: valid entries=26`.
> - Pytest re-measured on 2026-10-21 on that package tree (`971c04c`), Python 3.12.3, pytest 9.1.1, with the CI command `pytest --cov=a2a_gate --cov-report=term-missing --cov-report=json:coverage.json --cov-fail-under=80` [REPO]: **44 passed**, coverage **92.45%** (the total pytest-cov printed). The same run printed `CoverageWarning: Module a2a_gate was previously imported, but not measured`. The previously published README line was 19 passed and 89.42% on `c006882`. `docs/METRICS.md` records the same 2026-10-21 pytest line.

---

## 0. What the lab actually does (technical base, [REPO])

- An A2A-style back-office agent **proposes** actions. A **YAML policy** decides `auto`, `needs_approval`, or `forbidden`. **Another person** approves: the requester cannot approve their own request. A **hash-chained log** records the decision, and a **kill switch** stops later effects.
- Lab policy (`src/a2a_gate/data/nube_austral.yaml`, applied in `src/a2a_gate/policy.py`) [REPO]:
  - `issue_credit_note`: auto below 5000 cents, needs approval from 5000 through 500000 inclusive, forbidden above 500000, and forbidden at 0 or below;
  - `change_supplier_bank`: always needs approval;
  - `send_customer_notice` and `procurement_exception`: forbidden;
  - approval TTL: 3600 s;
  - approver roles: `finance_approver` and `admin`.
- The planner **never** sets the amount (it comes from the ledger), **never** chooses the idempotency key, and **never** approves itself [REPO]. See the README architecture section and [docs/adr/0007-ledger-amount.md](adr/0007-ledger-amount.md).
- Evals: **37 cases** (12 happy, 12 edge, 13 adversarial) in `evals/cases.json`, scored on invariants, not transcripts [REPO]:
  - no risky effect without approval;
  - no self-approval;
  - a rejection stays a rejection;
  - nothing effectful after the kill switch;
  - the hash chain verifies;
  - notes, emails, account numbers, and secrets stay out of the log.
- Measured [REPO], from the README sample above:
  - **37/37** with exit 0;
  - forced regression with exit 1 (`risky effect without approval`);
  - demo: 1 effect applied and the next one blocked by the kill switch, `valid entries=26`.
- **Live, planner only** (xAI `grok-4.20-0309-non-reasoning`, scripted approvals, one prompt) [REPO]. Sources: [docs/live/native_v2/REPORT.md](live/native_v2/REPORT.md), each `summary.json`, and the README section "Live measurement (xAI)".
  - Native client, 2 passes (main `6a2934b`): invariants 37/37 and 37/37; expectations 35/37 and 35/37; 10 effects applied and 0 duplicates on each pass (`results.json` sums to 10; `duplicate_applied` is 0); 35 calls, all HTTP 200.
  - `cost_usd`: **0.01081415** and **0.00670525** (total US$0.0175, the README rounding of the sum).
  - p50/p95 in seconds: **0.6463 / 0.8054899999999998** and **0.5826 / 0.7286899999999998**.
  - Tokens: 13,591 in, and 702 / 725 out.
  - Safety counts on both passes: 0 unauthorized effects, 0 without approval, 0 self-approvals, 0 rejected-then-executed, 0 effects after the kill switch, 0 injections obeyed.
  - Earlier scratch-client runs: run1 `0.00727535`, run2 `0.00620455`, run3 `0.00643835`, probe `0.01057035`; invariants 37/37 on all four (`docs/live/*/summary.json`).
  - The repo says this is **a small sample, not a proof**: a rare violation would not show.
- What the repo does **not** do [REPO]: a real IdP, a real ledger, an approval channel (email/Slack), hosting, multi-tenant, reversing an effect that already applied, or a model in the approver's seat. The shadow phase is design only ([docs/SCOPE.md](SCOPE.md)).

---

## 1. Business challenge [SYN]

The fictional insurer has a claims agent that asks a back-office agent for:

- **credit notes / premium refunds** (~**600 per month** [SYN]);
- **supplier bank-account changes** (repair shops, assessors).

Today one person prepares and checks each note: ~**20 min** [REPO-EST: the repo uses 20 min in `docs/BUSINESS_CASE.md`]. Bank changes arrive by email and are the usual impersonation-fraud path. Last year there were **about 2 wrong notes per month, caught by a second person** [REPO-EST: `docs/BUSINESS_CASE.md` says "Wrong notes caught by a second person | 2 / month"]. Each one costs **USD 300** on average [SYN]. A **payment-diversion attempt** would cost about **USD 25,000** [SYN] if it went through. They want the agent to prepare the work, **without the agent being able to pay or change accounts on its own**.

## 2. Objectives and sponsor [SYN]

- **Executive sponsor:** CFO of the fictional insurer. **Owner of the policy and of the approvers:** Finance. **Owner of the log, the kill switch, and rollback:** Platform. That is the same split the repo describes [REPO] (README, "Business strategy").
- O1. The agent prepares the credit notes and the person **only approves**: from 20 to 4 min per note [REPO-EST].
- O2. **Zero risky effects without a second person**, zero self-approvals, and zero rejections that later execute. The lab invariant is narrower [REPO]: zero risky effects **without approval**. A credit note under 5000 cents is `auto` and does not wait for a second person.
- O3. **Zero bank changes without approval**, and injections in notes or emails do not move accounts.
- O4. Auditable evidence (hash chain) and a kill switch a named role can operate.

## 3. Plan KPIs

| KPI | Category (BVR / Cloud Value Framework) | Baseline | Target | How it is measured | Stage |
|---|---|---|---|---|---|
| Eval-gate invariants in CI | Operational resilience | 37/37 in the lab [REPO] | 37/37 or more on every PR, with the insurer's own cases (≥60) [SYN] | `python -m a2a_gate.evalkit run` (exit 0) plus a forced regression with exit 1 [REPO] | 1. Activation |
| Risky effects executed without a second person | Risk / resilience | No systematic control [SYN]. The lab invariant is 0 risky effects without approval in the cassette cases and in the live sample [REPO]. Auto effects under 5000 cents do not use a second person [REPO] | 0 risky effects without approval [REPO: invariant] | Count in the hash-chained evidence plus `verify-evidence` [REPO] | 1. Activation (shadow) → 2. Scale |
| Self-approvals that executed | Risk | Not measured [SYN] | 0 [REPO: invariant] | Evidence: requester distinct from approver [REPO] | 2. Scale |
| Rejected-then-executed / duplicates | Risk | ~2 wrong notes per month [REPO-EST] | 0 [SYN] | Idempotency plus evidence; reversals counted by Finance [REPO for the lab, SYN for production] | 2. Scale |
| Supplier bank changes without approval | Risk / fraud | Email process with no dual control [SYN] | 0; 100% with a second person [SYN] | Evidence for `change_supplier_bank` [REPO] | 2. Scale |
| Minutes per credit note | Productivity | 20 min [REPO-EST] | 4 min [REPO-EST] | Time sampling in shadow (phase 1) and then in production [SYN] | 1. Activation → 2. Scale |
| Pending → decision (median) | Business agility | Not measured [SYN] | ≤4 business hours, inside the configured TTL [SYN; lab TTL is 3600 s, REPO] | Timestamps of `approval_requested` versus the decision in the evidence [REPO] | 2. Scale |
| Audit-log integrity | Resilience / compliance | Loose logs [SYN] | 100% of chains valid at the monthly audit [SYN] | `verify-evidence` (the demo prints `valid entries=26`) [REPO] | 3. Value retention |
| Kill-switch drill | Operational resilience | Never rehearsed [SYN] | 1 per quarter, with 0 later effects [SYN; the lab blocks post-kill effects, REPO] | Evidence of `kill_switch` plus `effect_blocked` [REPO] | 3. Value retention |
| LLM cost per proposed action | Cost savings | n/a | <USD 0.001 [SYN]; the repo's live sample is about USD 0.00019–0.00031 per call (`cost_usd` / 35) [REPO, small sample] | Provider cost ticks per call [REPO] | 3. Value retention |

> Note: the repo measures invariants, applied effects, duplicates, live-planner cost and latency, and evidence integrity. It does **not** measure minutes per note, fraud avoided, human approval time, or reversals on a real ledger. The customer would have to measure those business KPIs.

Per-call rates from the native passes [REPO]: `0.00670525 / 35` ≈ 0.000192 and `0.01081415 / 35` ≈ 0.000309. The range above is that pair, rounded.

## 4. Stages ("pit stops") with exit criteria [SYN, structure inspired by BVR]

1. **Activation / shadow** (weeks 1–6)
   - Work: adapt the YAML policy to thresholds in real currency, add ≥60 cases of their own (including adversarial impersonation cases), and run in **shadow**: the agent proposes and a person still enters the note by hand.
   - Shadow, the IdP, and the ledger connector have to be **built**: in the repo they are design only [REPO].
   - *Exit:* eval gate green and forced regression red in CI; 0 risky effects without approval in shadow; minutes per note measured on a sample; named owners for the policy and for the kill switch (that named-owner split is a phase-0 exit criterion in [docs/SCOPE.md](SCOPE.md)).
2. **Scale: one gated action** (months 2–4)
   - Work: `issue_credit_note` posts to the system of record after approval; `change_supplier_bank` is added later, still with a second person.
   - *Exit:* 0 self-approvals, 0 rejected-then-executed, 0 duplicates; ≤4 h to a decision; ≤4 min per note.
3. **Value retention** (months 5–12)
   - Work: monthly chain audit, quarterly kill-switch drill, and threshold recalibration with Finance.
   - *Exit:* 100% of chains valid; reversals and fraud counted by Finance.

**Client confirmation:** at the close of each stage, the CFO and Internal Audit sign a note that confirms the KPIs with evidence attached (eval reports, `verify-evidence`, Finance counts). This follows the BVR idea that **the customer attests the results**.

## 5. ROI (year 1) [ALL SYNTHETIC, except where tagged]

**Formulas:** ROI = (benefit − cost) / cost. Payback (months) = initial investment / net benefit per month, where net benefit per month = (benefit − recurring costs) / 12.

**Benefit assumptions:**

| Item | Calculation | USD/year |
|---|---|---:|
| A. Time saved on notes | 600 notes/month [SYN] × (20 − 4) min [REPO-EST] ÷ 60 × 12 = 1,920 h × USD 25/h [SYN] | 48,000 |
| B. One payment diversion avoided | 1 × USD 25,000 [SYN] | 25,000 |
| C. Wrong notes avoided | 2/month [REPO-EST] × 12 × USD 300 [SYN] | 7,200 |

**Cost assumptions** [SYN]:

| Item | Calculation | USD |
|---|---|---:|
| Integration: IdP, ledger connector, approval channel (initial investment) | 400 h × USD 50/h | 20,000 |
| Shadow phase (initial investment) | 80 h × USD 50/h | 4,000 |
| LLM | budget USD 50/year [SYN]. The repo's higher live per-call rate is about USD 0.000309 (`0.01081415 / 35`) [REPO, small sample]. 7,200 calls/year [SYN] × that rate ≈ USD 2.2/year [SYN]. That annual figure is not a total measured in the repo | 50 |
| Maintenance | 8 h/month × USD 50 × 12 | 4,800 |
| **Total cost** | | **28,850** |

**Results:**

| Scenario | Benefit | ROI | Payback |
|---|---:|---:|---:|
| **Base** (A + B + C) | 80,200 | (80,200 − 28,850) / 28,850 ≈ **178%** | 24,000 / ((80,200 − 4,850) / 12 = 6,279/month) ≈ **3.8 months** |
| **Conservative**: the person re-checks half the form (8 min saved), no diversion avoided (A' + C) | 31,200 | ≈ **8%** | ≈ **10.9 months** |
| **Minimum**: the person re-checks everything (0 min saved), only C | 7,200 | ≈ **−75%** | **does not pay back** in the year (≈122 months) |

**Honest reading:**
- The base case depends on two things **the repo does not measure**: that the person really only approves, and that there are fraud attempts to stop.
- The repo already warns, in `docs/BUSINESS_CASE.md`: if discovery shows the person re-checks every field, the 4 minutes are wrong and savings should not be promised.
- The robust value is **control**: 0 effects without a second person on the actions that need one, rejections that stay rejected, and an auditable log. That is easier to defend to Audit than to Finance.

## 6. Risks

| Risk | Source | Mitigation |
|---|---|---|
| 37/37 clean invariants is "a good sign, not a proof": a rare violation would not show up in a small sample | [REPO] | More cases of their own, repeated runs, and continuous monitoring of production evidence |
| The live sample measured **only the planner**, with scripted approvals, one model, and one prompt | [REPO] | Repeat with the real prompt and measure human approvers in shadow |
| Two cases (`edge_unknown_action`, `adv_injection_compromised`) do not reproduce with a model that behaves: the malicious planner is scripted | [REPO] | Keep those cases on cassette; do not confuse an expectation match with a model score |
| The log detects tampering after the fact and does not prevent it | [REPO] | WORM or append-only storage, plus separated access |
| There is no IdP, real ledger, or approval channel: they have to be built | [REPO] | Integration budget (USD 20,000 [SYN]) |
| An effect that already applied cannot be reversed | [REPO] | Manual reversal by Finance, plus a rehearsed kill switch |
| Approvers click through without reading (rubber-stamping) | [SYN] | Sample approvals, limits per approver, rotation |
| The volume, rate, and fraud assumptions are invented | [SYN] | Replace them in discovery with the customer's data |
