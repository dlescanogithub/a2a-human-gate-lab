"""Load scripted cases. The files are the contract; the runner does not invent them."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from a2a_gate.jsonutil import as_bool, as_dict, as_int, as_list, as_optional_str, as_str, loads
from a2a_gate.types import Proposal

_CATEGORIES = frozenset({"happy", "edge", "adversarial"})
_OPS = frozenset({"approve", "reject", "cancel", "advance"})
_KILL = frozenset({"", "before_create", "before_decisions"})
_PROBES = frozenset({"", "secret"})


@dataclass(frozen=True)
class Decision:
    op: str
    actor_id: str
    actor_role: str
    action: str
    record_id: str
    seconds: int
    expect_error: str


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    title: str
    requester_id: str
    requester_role: str
    message: str
    record_id: str
    idempotency_key: str
    proposals: tuple[Proposal, ...]
    tokens_in: int
    tokens_out: int
    decisions: tuple[Decision, ...]
    downstream_failures: int
    kill_at: str
    use_fake_planner: bool
    probe: str
    replay_create: bool
    expect_state: str
    expect_applied: int
    expect_error: str


def load_cases(path: Path) -> tuple[EvalCase, ...]:
    raw = loads(path.read_text(encoding="utf-8"))
    items = as_list(raw, "cases")
    cases = tuple(_case(item) for item in items)
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate eval case id")
    return cases


def load_case(path: Path) -> EvalCase:
    return _case(loads(path.read_text(encoding="utf-8")))


def _case(value: object) -> EvalCase:
    raw = as_dict(value)
    category = as_str(raw.get("category"), "category")
    if category not in _CATEGORIES:
        raise ValueError("bad category")
    kill_at = as_optional_str(raw.get("kill_at"), "kill_at")
    if kill_at not in _KILL:
        raise ValueError("bad kill_at")
    probe = as_optional_str(raw.get("probe"), "probe")
    if probe not in _PROBES:
        raise ValueError("bad probe")
    proposals = tuple(_proposal(item) for item in as_list(raw.get("proposals"), "proposals"))
    decisions = tuple(_decision(item) for item in as_list(raw.get("decisions"), "decisions"))
    return EvalCase(
        id=as_str(raw.get("id"), "id"),
        category=category,
        title=as_str(raw.get("title"), "title"),
        requester_id=as_str(raw.get("requester_id"), "requester_id"),
        requester_role=as_str(raw.get("requester_role"), "requester_role"),
        message=as_str(raw.get("message"), "message"),
        record_id=as_str(raw.get("record_id"), "record_id"),
        idempotency_key=as_optional_str(raw.get("idempotency_key"), "idempotency_key"),
        proposals=proposals,
        tokens_in=as_int(raw.get("tokens_in"), "tokens_in"),
        tokens_out=as_int(raw.get("tokens_out"), "tokens_out"),
        decisions=decisions,
        downstream_failures=as_int(raw.get("downstream_failures"), "downstream_failures"),
        kill_at=kill_at,
        use_fake_planner=as_bool(raw.get("use_fake_planner"), "use_fake_planner"),
        probe=probe,
        replay_create=as_bool(raw.get("replay_create"), "replay_create"),
        expect_state=as_str(raw.get("expect_state"), "expect_state"),
        expect_applied=as_int(raw.get("expect_applied"), "expect_applied"),
        expect_error=as_optional_str(raw.get("expect_error"), "expect_error"),
    )


def _proposal(value: object) -> Proposal:
    raw = as_dict(value)
    claims_raw = raw.get("claims", {})
    claims_obj = as_dict(claims_raw)
    claims = tuple((key, as_str(claims_obj[key], "claim")) for key in sorted(claims_obj))
    return Proposal(
        action=as_str(raw.get("action"), "action"),
        record_id=as_str(raw.get("record_id"), "record_id"),
        claims=claims,
    )


def _decision(value: object) -> Decision:
    raw = as_dict(value)
    op = as_str(raw.get("op"), "op")
    if op not in _OPS:
        raise ValueError("bad op")
    if op == "advance":
        return Decision(
            op=op,
            actor_id="",
            actor_role="",
            action="",
            record_id="",
            seconds=as_int(raw.get("seconds"), "seconds"),
            expect_error="",
        )
    if op == "cancel":
        return Decision(
            op=op,
            actor_id=as_str(raw.get("actor_id"), "actor_id"),
            actor_role=as_str(raw.get("actor_role"), "actor_role"),
            action="",
            record_id="",
            seconds=0,
            expect_error=as_optional_str(raw.get("expect_error"), "expect_error"),
        )
    return Decision(
        op=op,
        actor_id=as_str(raw.get("actor_id"), "actor_id"),
        actor_role=as_str(raw.get("actor_role"), "actor_role"),
        action=as_str(raw.get("action"), "action"),
        record_id=as_str(raw.get("record_id"), "record_id"),
        seconds=0,
        expect_error=as_optional_str(raw.get("expect_error"), "expect_error"),
    )
