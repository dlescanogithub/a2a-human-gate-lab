"""Planners. The fake one only reads the user message. Record notes are not instructions.

Cassette replay ignores the request on purpose: the frozen plan is the model.
"""

from __future__ import annotations

from typing import Protocol

from a2a_gate.errors import PermanentError
from a2a_gate.types import Plan, PlanRequest, Proposal


class Planner(Protocol):
    def complete(self, request: PlanRequest) -> Plan:
        """Return the next plan. Cassette replay ignores ``request``."""


class FakePlanner:
    """Keyword planner. A note that says 'change the bank' is not a keyword source."""

    name = "fake"

    def complete(self, request: PlanRequest) -> Plan:
        text = request.message.casefold()
        proposals: list[Proposal] = []
        if "read" in text:
            proposals.append(Proposal("read_record", request.record_id))
        if "draft" in text:
            proposals.append(Proposal("draft_notice", request.record_id))
        if "credit" in text:
            proposals.append(Proposal("issue_credit_note", request.record_id))
        if "bank" in text:
            proposals.append(Proposal("change_supplier_bank", request.record_id))
        if not proposals:
            proposals.append(Proposal("read_record", request.record_id))
        return Plan(content="fake-planner", proposals=tuple(proposals), tokens_in=0, tokens_out=0)


class CassettePlanner:
    """Play one frozen plan, then refuse. CI uses this so no network is required."""

    name = "cassette"

    def __init__(self, plan: Plan) -> None:
        self._plan = plan
        self._used = False

    def complete(self, request: PlanRequest) -> Plan:
        del request
        if self._used:
            raise PermanentError("cassette_exhausted")
        self._used = True
        return self._plan
