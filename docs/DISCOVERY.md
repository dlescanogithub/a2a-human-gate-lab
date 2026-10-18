# Discovery

Ten questions to ask before copying this lab into a real back office. Nube Austral is not that office. Each answer changes the design.

1. **Who may approve, and may the requester be that person?**
   If the same person must be able to approve, this design is the wrong one. The runtime rejects that on actor id, not only on role. You would be choosing a different control, and you should say so.

2. **What are the thresholds for auto, approval, and forbidden?**
   The YAML uses 5000 and 500000 fictional cents. A real answer replaces those numbers. If every credit note needs a person, delete the auto band. If nothing may auto-post, the eval cases for `hp_credit_auto` become regressions.

3. **How long may an approval stay pending?**
   The lab uses 3600 seconds. A shorter SLA means a faster expiry and a queue metric. A longer one changes the runbook for a stuck queue.

4. **What must the audit record contain before finance accepts the effect?**
   Today the chain stores ids, amounts, roles, and reason codes. It does not store the customer note. If finance wants the note, that is a new redaction decision, not a free-text log.

5. **Which system of record owns the amount?**
   This lab trusts the catalog, not the model. If the real amount lives in an ERP, the gate must read it at execution time. If the model is allowed to type the amount, the `adv_fake_amount` case is the one you are choosing to lose.

6. **Can a rejection be undone?**
   Here it cannot. Replay returns the rejected task. If the business undoes rejections, that needs a new idempotency key and a written reason, not a second click on the same task.

7. **Who may engage the kill switch, and how often do you drill it?**
   The lab requires an admin role plus `ADMIN_TOKEN` from the environment. A drill that nobody owns will fail the day you need it. See the runbook.

8. **Is the first pilot really one action type?**
   Scope says yes: credit notes. Bank-account changes are implemented here as a second action because the adversarial story needs them. A real phase 1 can still ship only credit notes.

9. **Where do pending approvals get seen?**
   Email and Slack are design-only. If the answer is "a mailbox", the lab has nowhere to send it. Build the channel only after the gate's invariants already hold without it.

10. **What is the rollback if a note posted and should not have?**
    The kill switch does not reverse the fake ledger. A real answer is a reversing entry in the system of record, with its own approval. If nobody can name that entry, do not turn the gate on.
