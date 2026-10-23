"""Task lifecycle.

The planner proposes. This module decides what may reach the downstream
ledger. A model claim never approves itself, never sets the amount, and never
chooses the idempotency key.

``enforce_gate=False`` exists only so the forced-regression harness can show
the invariant check going red. ``build_runtime`` (serve and demo) always
leaves it True.
"""

from __future__ import annotations

import logging
import random
import threading
from collections.abc import Callable

from a2a_gate.catalog import Record, get_record
from a2a_gate.clock import Clock
from a2a_gate.downstream import FakeDownstream, call_with_retries
from a2a_gate.errors import AuthError, ValidationError
from a2a_gate.evidence import EvidenceLog
from a2a_gate.logging_setup import log
from a2a_gate.planner import Planner
from a2a_gate.policy import Disposition, Policy
from a2a_gate.tokens import tokens_equal
from a2a_gate.types import ActionState, Actor, EffectStatus, PlanRequest, Proposal, Task, TaskState

EFFECTFUL = frozenset({"issue_credit_note", "change_supplier_bank"})
LOCAL = frozenset({"read_record", "draft_notice"})
TERMINAL = frozenset({"completed", "failed", "canceled", "rejected"})
DRAFT_BODY = "Local draft. Not sent."

LOGGER = logging.getLogger("a2a_gate.runtime")


def effect_key(task_key: str, action: str, record_id: str) -> str:
    return f"{task_key}:{action}:{record_id}"


def rollup(task: Task) -> TaskState:
    if any(action.effect_status in ("dead_letter", "blocked") for action in task.actions):
        return "failed"
    if any(action.approval == "pending" for action in task.actions):
        return "input-required"
    if any(action.reason_code == "forbidden" for action in task.actions):
        return "rejected"
    return "completed"


def reason_for(task: Task) -> str:
    if task.state == "input-required":
        return "approval-pending"
    if task.state == "failed":
        if any(action.reason_code == "kill_switch" for action in task.actions):
            return "kill-switch"
        return "dead_letter"
    if task.state == "rejected":
        if any(action.reason_code == "expired" for action in task.actions):
            return "approval-expired"
        if any(action.reason_code == "rejected" for action in task.actions):
            return "rejected"
        return "forbidden"
    if task.state == "completed":
        if not task.actions:
            return "no_actions"
        return "completed"
    return task.state


def task_payload(task: Task) -> dict[str, object]:
    """Public task view. Notes, emails, and account numbers are not included."""

    return {
        "id": task.id,
        "contextId": task.context_id,
        "status": {"state": task.state, "reason": task.status_reason},
        "requesterId": task.requester_id,
        "idempotencyKey": task.idempotency_key,
        "createdAt": task.created_at,
        "actions": [_action_payload(action) for action in task.actions],
        "drafts": [{"recordId": item["record_id"]} for item in task.drafts],
        "labSimplified": True,
    }


def _action_payload(action: ActionState) -> dict[str, object]:
    return {
        "action": action.action,
        "recordId": action.record_id,
        "amountCents": action.amount_cents,
        "effectKey": action.effect_key,
        "disposition": action.disposition,
        "approval": action.approval,
        "effectStatus": action.effect_status,
        "attempts": action.attempts,
        "reasonCode": action.reason_code,
        "decidedBy": action.decided_by,
        "expiresAt": action.expires_at,
    }


class Runtime:
    def __init__(
        self,
        *,
        policy: Policy,
        evidence: EvidenceLog,
        downstream: FakeDownstream,
        clock: Clock,
        planner: Planner,
        admin_token: str,
        enforce_gate: bool = True,
        max_attempts: int = 3,
        rng: random.Random | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.policy = policy
        self.evidence = evidence
        self.downstream = downstream
        self.clock = clock
        self.planner = planner
        self.admin_token = admin_token
        self.enforce_gate = enforce_gate
        self.max_attempts = max_attempts
        self.rng = rng if rng is not None else random.Random(0)
        self.sleeper: Callable[[float], None] = sleeper if sleeper is not None else _noop_sleep
        self.killed = False
        self.tasks: dict[str, Task] = {}
        self.by_idem: dict[str, str] = {}
        self.applied_keys: dict[str, EffectStatus] = {}
        self._counter = 0
        self._lock = threading.Lock()

    def kill(self, token: str, actor: Actor) -> None:
        with self._lock:
            if not tokens_equal(token, self.admin_token):
                raise AuthError("admin_token")
            if actor.role != "admin":
                raise AuthError("wrong_role")
            self.killed = True
            self._emit(
                event="kill_switch",
                reason_code="kill_switch",
                actor_id=actor.id,
                actor_role=actor.role,
            )

    def create_task(
        self,
        requester: Actor,
        message: str,
        record_id: str,
        idempotency_key: str,
        *,
        case_id: str = "",
        record: Record | None = None,
    ) -> Task:
        with self._lock:
            return self._create(requester, message, record_id, idempotency_key, case_id, record)

    def approve(self, task_id: str, actor: Actor, action_name: str, record_id: str) -> Task:
        with self._lock:
            return self._decide(task_id, actor, action_name, record_id, reject=False)

    def reject(self, task_id: str, actor: Actor, action_name: str, record_id: str) -> Task:
        with self._lock:
            return self._decide(task_id, actor, action_name, record_id, reject=True)

    def cancel(self, task_id: str, actor: Actor) -> Task:
        with self._lock:
            task = self._require(task_id)
            if task.state in TERMINAL:
                return task
            if actor.id != task.requester_id and actor.role != "admin":
                raise AuthError("wrong_role")
            task.state = "canceled"
            task.status_reason = "canceled"
            for action in task.actions:
                if action.approval == "pending":
                    action.approval = "rejected"
                    action.reason_code = "canceled"
                    action.decided_by = actor.id
            self._emit(
                event="task_canceled",
                task=task,
                reason_code="canceled",
                actor_id=actor.id,
                actor_role=actor.role,
            )
            return task

    def snapshot(self, task_id: str) -> dict[str, object]:
        with self._lock:
            return task_payload(self._require(task_id))

    def _create(
        self,
        requester: Actor,
        message: str,
        record_id: str,
        idempotency_key: str,
        case_id: str,
        record: Record | None,
    ) -> Task:
        if idempotency_key == "":
            raise ValidationError("missing_idempotency")
        if record is not None and record.id != record_id:
            raise ValidationError("record_mismatch")
        existing = self.by_idem.get(idempotency_key)
        if existing is not None:
            return self.tasks[existing]
        self._counter += 1
        task = Task(
            id=f"task_{self._counter:04d}",
            context_id=f"ctx_{self._counter:04d}",
            idempotency_key=idempotency_key,
            state="submitted",
            status_reason="submitted",
            requester_id=requester.id,
            requester_role=requester.role,
            created_at=self.clock.time(),
        )
        self.tasks[task.id] = task
        self.by_idem[idempotency_key] = task.id
        self._emit(event="task_submitted", task=task, reason_code="submitted")
        task.state = "working"
        task.status_reason = "working"
        self._emit(event="task_working", task=task, reason_code="working")

        loaded = record if record is not None else get_record(record_id)
        if loaded is None:
            return self._fail(task, "unknown_record")

        plan = self.planner.complete(
            PlanRequest(message=message, record_id=record_id, case_id=case_id)
        )
        ignored = sum(len(item.claims) for item in plan.proposals)
        self._emit(
            event="plan_recorded",
            task=task,
            reason_code="ok",
            tokens_in=plan.tokens_in,
            tokens_out=plan.tokens_out,
            proposal_count=len(plan.proposals),
            ignored_claims=ignored,
        )
        if not plan.proposals:
            task.state = "completed"
            task.status_reason = "no_actions"
            self._emit(event="task_state", task=task, reason_code="no_actions")
            return task
        for proposal in plan.proposals:
            self._add_action(task, requester, proposal, record)
        self._close(task)
        return task

    def _add_action(
        self,
        task: Task,
        requester: Actor,
        proposal: Proposal,
        overlay: Record | None,
    ) -> None:
        target = _target_record(proposal.record_id, overlay)
        disposition: Disposition
        if target is None:
            amount = 0
            disposition = "forbidden"
        elif proposal.action == "issue_credit_note":
            amount = target.amount_cents
            disposition = self.policy.classify(proposal.action, amount)
        else:
            amount = 0
            disposition = self.policy.classify(proposal.action, amount)
        action = ActionState(
            action=proposal.action,
            record_id=proposal.record_id,
            amount_cents=amount,
            effect_key=effect_key(task.idempotency_key, proposal.action, proposal.record_id),
            disposition=disposition,
            approval="not_required",
            effect_status="not_run",
            attempts=0,
            reason_code="ok",
            requested_by=requester.id,
        )
        task.actions.append(action)
        if disposition == "forbidden":
            action.reason_code = "forbidden"
            self._emit(event="action_forbidden", task=task, action=action, reason_code="forbidden")
            return
        if disposition == "needs_approval" and self.enforce_gate:
            action.approval = "pending"
            action.expires_at = self.clock.time() + self.policy.approval_ttl_seconds
            action.reason_code = "approval_pending"
            self._emit(
                event="approval_requested",
                task=task,
                action=action,
                reason_code="approval_pending",
            )
            return
        if disposition == "needs_approval":
            action.reason_code = "gate_bypassed"
        self._execute(task, action)

    def _execute(self, task: Task, action: ActionState) -> None:
        if action.action not in EFFECTFUL:
            if action.action == "draft_notice":
                task.drafts.append({"record_id": action.record_id, "body": DRAFT_BODY})
            action.effect_status = "not_run"
            action.reason_code = "ok"
            self._emit(event="local_action", task=task, action=action, reason_code="ok")
            return
        if self.killed:
            action.effect_status = "blocked"
            action.reason_code = "kill_switch"
            self._emit(event="effect_blocked", task=task, action=action, reason_code="kill_switch")
            return
        prior = self.applied_keys.get(action.effect_key)
        if prior is not None:
            action.effect_status = prior
            action.reason_code = "replay"
            self._emit(event="effect_replay", task=task, action=action, reason_code="replay")
            return
        result = call_with_retries(
            self.downstream,
            action.effect_key,
            max_attempts=self.max_attempts,
            rng=self.rng,
            sleeper=self.sleeper,
        )
        action.attempts = result.attempts
        action.effect_status = result.status
        action.reason_code = "ok" if result.status == "applied" else "dead_letter"
        self.applied_keys[action.effect_key] = result.status
        event = "effect_applied" if result.status == "applied" else "effect_dead_letter"
        self._emit(event=event, task=task, action=action, reason_code=action.reason_code)

    def _decide(
        self,
        task_id: str,
        actor: Actor,
        action_name: str,
        record_id: str,
        *,
        reject: bool,
    ) -> Task:
        task = self._require(task_id)
        if task.state in TERMINAL:
            return task
        action = self._find(task, action_name, record_id)
        if action.approval == "rejected":
            return task
        if actor.id == task.requester_id:
            self._emit(
                event="approval_denied",
                task=task,
                action=action,
                reason_code="self_approval",
                actor_id=actor.id,
                actor_role=actor.role,
            )
            raise AuthError("self_approval")
        if actor.role not in self.policy.approver_roles:
            self._emit(
                event="approval_denied",
                task=task,
                action=action,
                reason_code="wrong_role",
                actor_id=actor.id,
                actor_role=actor.role,
            )
            raise AuthError("wrong_role")
        if action.approval != "pending":
            raise ValidationError("not_pending")
        if action.expires_at is not None and self.clock.time() >= action.expires_at:
            action.approval = "expired"
            action.reason_code = "expired"
            task.state = "rejected"
            task.status_reason = "approval-expired"
            self._emit(
                event="approval_expired",
                task=task,
                action=action,
                reason_code="expired",
                actor_id=actor.id,
                actor_role=actor.role,
            )
            return task
        if self.killed:
            action.effect_status = "blocked"
            action.reason_code = "kill_switch"
            task.state = "failed"
            task.status_reason = "kill-switch"
            self._emit(
                event="effect_blocked",
                task=task,
                action=action,
                reason_code="kill_switch",
                actor_id=actor.id,
                actor_role=actor.role,
            )
            return task
        if reject:
            action.approval = "rejected"
            action.decided_by = actor.id
            action.reason_code = "rejected"
            task.state = "rejected"
            task.status_reason = "rejected"
            self._emit(
                event="task_rejected",
                task=task,
                action=action,
                reason_code="rejected",
                actor_id=actor.id,
                actor_role=actor.role,
            )
            return task
        action.approval = "approved"
        action.decided_by = actor.id
        self._emit(
            event="approval_granted",
            task=task,
            action=action,
            reason_code="ok",
            actor_id=actor.id,
            actor_role=actor.role,
        )
        self._execute(task, action)
        self._close(task)
        return task

    def _close(self, task: Task) -> None:
        task.state = rollup(task)
        task.status_reason = reason_for(task)
        self._emit(event="task_state", task=task, reason_code=task.status_reason)

    def _fail(self, task: Task, reason_code: str) -> Task:
        task.state = "failed"
        task.status_reason = reason_code
        self._emit(event="task_state", task=task, reason_code=reason_code)
        return task

    def _require(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if task is None:
            raise ValidationError("unknown_task")
        return task

    def _find(self, task: Task, action_name: str, record_id: str) -> ActionState:
        matches = [
            action
            for action in task.actions
            if action.action == action_name and action.record_id == record_id
        ]
        if not matches:
            raise ValidationError("unknown_action")
        for action in matches:
            if action.approval == "pending":
                return action
        return matches[0]

    def _emit(
        self,
        *,
        event: str,
        reason_code: str,
        task: Task | None = None,
        action: ActionState | None = None,
        actor_id: str = "",
        actor_role: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        proposal_count: int = 0,
        ignored_claims: int = 0,
    ) -> None:
        fields: dict[str, object] = {
            "task_id": "" if task is None else task.id,
            "action": "" if action is None else action.action,
            "record_id": "" if action is None else action.record_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "amount_cents": 0 if action is None else action.amount_cents,
            "disposition": "" if action is None else action.disposition,
            "approval": "" if action is None else action.approval,
            "effect_status": "" if action is None else action.effect_status,
            "attempts": 0 if action is None else action.attempts,
            "reason_code": reason_code,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "proposal_count": proposal_count,
            "ignored_claims": ignored_claims,
        }
        self.evidence.append(event, **fields)
        log(LOGGER, logging.INFO, event, **fields)


def _target_record(record_id: str, overlay: Record | None) -> Record | None:
    if overlay is not None and overlay.id == record_id:
        return overlay
    return get_record(record_id)


def _noop_sleep(delay: float) -> None:
    del delay
