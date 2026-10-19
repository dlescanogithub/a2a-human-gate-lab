"""Project a finished action into the live call log.

The gate already stores disposition, approval, effect status, and a reason
code. This module copies those into a fixed vocabulary. It does not decide
policy. Names that are not short tokens become ``redacted_name`` so a note,
an email, or a free-text parameter cannot land in the log.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

_NAME = re.compile(r"[a-z][a-z0-9_]{0,64}")
_REASONS = frozenset({"forbidden", "rejected", "expired", "kill_switch", "dead_letter", "canceled"})


@dataclass(frozen=True)
class ActionFact:
    """Fields the runtime already keeps on an action. No note, email, or amount."""

    action: str
    disposition: str
    approval: str
    effect_status: str
    reason_code: str


def safe_action_name(name: str) -> str:
    if _NAME.fullmatch(name):
        return name
    return "redacted_name"


def action_result(fact: ActionFact) -> dict[str, str]:
    """One whitelist object: action, result, and a rejection code when rejected."""

    name = safe_action_name(fact.action)
    if fact.effect_status == "applied":
        result = "executed"
    elif fact.approval == "pending":
        result = "input-required"
    elif (
        fact.disposition == "forbidden"
        or fact.approval in {"rejected", "expired"}
        or fact.effect_status in {"blocked", "dead_letter"}
    ):
        result = "rejected"
    else:
        result = "accepted"
    item = {"action": name, "result": result}
    if result == "rejected":
        code = fact.reason_code if fact.reason_code in _REASONS else "unlisted"
        item["reason_code"] = code
    return item


def proposal_names(facts: Sequence[ActionFact]) -> list[str]:
    return [safe_action_name(fact.action) for fact in facts]


def summarize_proposals(facts: Sequence[ActionFact]) -> dict[str, object]:
    """Counts for one live run. Separate from the published measurement table."""

    by_action: dict[str, int] = {}
    rejected = 0
    approval_requested = 0
    unknown_or_out_of_policy = 0
    for fact in facts:
        name = safe_action_name(fact.action)
        by_action[name] = by_action.get(name, 0) + 1
        if action_result(fact)["result"] == "rejected":
            rejected += 1
        if fact.disposition == "needs_approval":
            approval_requested += 1
        if fact.disposition == "forbidden":
            unknown_or_out_of_policy += 1
    return {
        "proposals_approval_requested": approval_requested,
        "proposals_by_action": dict(sorted(by_action.items())),
        "proposals_rejected": rejected,
        "proposals_unknown_or_out_of_policy": unknown_or_out_of_policy,
    }
