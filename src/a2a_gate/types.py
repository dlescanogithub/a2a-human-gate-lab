"""In-memory task and plan shapes. Not the A2A protobuf schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from a2a_gate.policy import Disposition

TaskState = Literal[
    "submitted",
    "working",
    "input-required",
    "completed",
    "failed",
    "canceled",
    "rejected",
]
ApprovalStatus = Literal["pending", "approved", "rejected", "expired", "not_required"]
EffectStatus = Literal["applied", "dead_letter", "blocked", "not_run"]


@dataclass(frozen=True)
class Actor:
    id: str
    role: str


@dataclass(frozen=True)
class Proposal:
    action: str
    record_id: str
    claims: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Plan:
    content: str
    proposals: tuple[Proposal, ...]
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class PlanRequest:
    message: str
    record_id: str
    case_id: str


@dataclass
class ActionState:
    action: str
    record_id: str
    amount_cents: int
    effect_key: str
    disposition: Disposition
    approval: ApprovalStatus
    effect_status: EffectStatus
    attempts: int
    reason_code: str
    requested_by: str
    decided_by: str = ""
    expires_at: int | None = None


@dataclass
class Task:
    id: str
    context_id: str
    idempotency_key: str
    state: TaskState
    status_reason: str
    requester_id: str
    requester_role: str
    created_at: int
    actions: list[ActionState] = field(default_factory=list)
    drafts: list[dict[str, str]] = field(default_factory=list)
