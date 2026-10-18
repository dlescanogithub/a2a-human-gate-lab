# 0002 Human gate and separation of duties

## Status

Accepted. 2026-10-18.

## Context

The planner can propose a credit note or a bank-account change, and it can claim the change is already approved. Low-risk reads and drafts should still finish.

## Decision

A YAML policy maps action and amount to auto, needs-approval, or forbidden. The requester's actor id cannot approve or reject. Approver roles are `finance_approver` and `admin`. Pending approvals expire. A human rejection is terminal and is what replay returns. Model claims (`skip_approval`, `already_approved`) are counted and ignored.

## Consequences

Auto credit notes under the threshold post without a second person. That is a policy choice, not an oversight. Raising the auto band to "never" is a YAML change plus an eval change. The server has no switch that disables the gate. Only the regression harness constructs `enforce_gate=False`.
