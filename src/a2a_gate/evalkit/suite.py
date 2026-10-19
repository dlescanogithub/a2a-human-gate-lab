"""Run the scripted cases and the forced regression.

A case fails when an invariant fails or the finished state disagrees with the
case file. The regression disables the gate on purpose and must trip
``risky effect without approval``.
"""

from __future__ import annotations

import io
import json
import logging
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from a2a_gate.catalog import get_record, with_note
from a2a_gate.clock import ManualClock
from a2a_gate.downstream import FakeDownstream
from a2a_gate.errors import GateLabError
from a2a_gate.evalkit.action_view import ActionFact
from a2a_gate.evalkit.cases import EvalCase, load_case, load_cases
from a2a_gate.evalkit.checks import SECRET_PROBE, invariant_failures
from a2a_gate.evidence import EvidenceLog, verify
from a2a_gate.logging_setup import JsonFormatter
from a2a_gate.planner import CassettePlanner, FakePlanner, Planner
from a2a_gate.policy import load_default_policy
from a2a_gate.runtime import Runtime
from a2a_gate.trace import Tracer
from a2a_gate.types import Actor, Plan, Task

ADMIN_TOKEN = "lab-admin"
LOGGER = logging.getLogger("a2a_gate.runtime")


@dataclass(frozen=True)
class Outcome:
    case_id: str
    state: str
    applied: int
    duplicate_applied: int
    errors: tuple[str, ...]
    invariants: tuple[str, ...]
    actions: tuple[ActionFact, ...]

    @property
    def ok(self) -> bool:
        return not self.errors and not self.invariants


@dataclass(frozen=True)
class Report:
    ok: bool
    text: str
    passed: int
    failed: int
    elapsed_ms: int
    failures: tuple[str, ...]


def run_suite(evals_dir: Path) -> Report:
    cases = load_cases(evals_dir / "cases.json")
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outcomes = tuple(run_case(case, root / case.id, enforce_gate=True) for case in cases)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    tracer = Tracer(evals_dir / "results", "eval-trace")
    for outcome in outcomes:
        tracer.emit(
            "case",
            case_id=outcome.case_id,
            ok=outcome.ok,
            state=outcome.state,
            applied=outcome.applied,
        )
    failed = [item for item in outcomes if not item.ok]
    lines = [
        f"eval gate: {'pass' if not failed else 'fail'}",
        f"cases: {len(outcomes)}",
        f"passed: {len(outcomes) - len(failed)}",
        f"failed: {len(failed)}",
        f"elapsed_ms: {elapsed_ms}",
        "provider: cassette",
    ]
    details = tuple(
        f"{item.case_id}: {', '.join(item.errors + item.invariants)}" for item in failed
    )
    lines.extend(details)
    return Report(
        ok=not failed,
        text="\n".join(lines),
        passed=len(outcomes) - len(failed),
        failed=len(failed),
        elapsed_ms=elapsed_ms,
        failures=details,
    )


def run_regression(evals_dir: Path) -> Report:
    case = load_case(evals_dir / "regressions" / "bypass_gate.json")
    with tempfile.TemporaryDirectory() as tmp:
        outcome = run_case(case, Path(tmp) / "regression", enforce_gate=False)
    tripped = "risky effect without approval" in outcome.invariants
    if tripped:
        text = "forced regression: fail\ninvariant: risky effect without approval"
    else:
        text = "forced regression: the invariant did not fire"
    return Report(
        ok=not tripped,
        text=text,
        passed=0 if tripped else 1,
        failed=1 if tripped else 0,
        elapsed_ms=0,
        failures=("risky effect without approval",) if tripped else (),
    )


def write_report(report: Report, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "elapsed_ms": report.elapsed_ms,
        "failed": report.failed,
        "failures": list(report.failures),
        "ok": report.ok,
        "passed": report.passed,
        "provider": "cassette",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_case(
    case: EvalCase,
    directory: Path,
    *,
    enforce_gate: bool,
    planner: Planner | None = None,
) -> Outcome:
    directory.mkdir(parents=True, exist_ok=True)
    clock = ManualClock()
    evidence_path = directory / "evidence.jsonl"
    probes: list[str] = []
    overlay = None
    if case.probe == "secret":
        base = get_record(case.record_id)
        if base is None:
            raise ValueError("probe record")
        overlay = with_note(base, SECRET_PROBE)
        probes.append(SECRET_PROBE)
    chosen: Planner
    if planner is not None:
        chosen = planner
    elif case.use_fake_planner:
        chosen = FakePlanner()
    else:
        chosen = CassettePlanner(
            Plan(
                content="cassette",
                proposals=case.proposals,
                tokens_in=case.tokens_in,
                tokens_out=case.tokens_out,
            )
        )
    runtime = Runtime(
        policy=load_default_policy(),
        evidence=EvidenceLog(evidence_path, clock),
        downstream=FakeDownstream(case.downstream_failures),
        clock=clock,
        planner=chosen,
        admin_token=ADMIN_TOKEN,
        enforce_gate=enforce_gate,
        max_attempts=3,
        rng=random.Random(0),
        sleeper=_no_sleep,
    )
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    previous = LOGGER.propagate
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    errors: list[str] = []
    task: Task | None = None
    try:
        if case.kill_at == "before_create":
            runtime.kill(ADMIN_TOKEN, Actor("admin.ops", "admin"))
        try:
            task = runtime.create_task(
                Actor(case.requester_id, case.requester_role),
                case.message,
                case.record_id,
                case.idempotency_key,
                case_id=case.id,
                record=overlay,
            )
        except GateLabError as exc:
            if exc.reason_code != case.expect_error:
                errors.append(f"create {exc.reason_code}")
        else:
            if case.expect_error:
                errors.append("missing create error")
            if case.kill_at == "before_decisions":
                runtime.kill(ADMIN_TOKEN, Actor("admin.ops", "admin"))
            task = _decisions(runtime, task, case, errors)
            if case.replay_create:
                task = runtime.create_task(
                    Actor(case.requester_id, case.requester_role),
                    case.message,
                    case.record_id,
                    case.idempotency_key,
                    case_id=case.id,
                    record=overlay,
                )
    finally:
        LOGGER.removeHandler(handler)
        LOGGER.propagate = previous
    if task is None:
        if case.expect_state != "validation_error":
            errors.append("missing task")
    elif task.state != case.expect_state:
        errors.append(f"state {task.state}")
    applied_keys = tuple(runtime.downstream.applied)
    applied = len(applied_keys)
    duplicate_applied = applied - len(set(applied_keys))
    if applied != case.expect_applied:
        errors.append(f"applied {applied}")
    ok, _detail = verify(evidence_path)
    evidence_text = evidence_path.read_text(encoding="utf-8")
    log_text = buffer.getvalue()
    invariants = invariant_failures(
        task,
        evidence_text,
        log_text,
        evidence_ok=ok,
        kill_engaged=case.kill_at != "",
        probes=tuple(probes),
    )
    return Outcome(
        case_id=case.id,
        state="" if task is None else task.state,
        applied=applied,
        duplicate_applied=duplicate_applied,
        errors=tuple(_unique(errors)),
        invariants=tuple(_unique(invariants)),
        actions=_action_facts(task),
    )


def _action_facts(task: Task | None) -> tuple[ActionFact, ...]:
    """Copy gate fields for the live logger. Amounts and record ids stay out."""

    if task is None:
        return ()
    return tuple(
        ActionFact(
            action=action.action,
            disposition=action.disposition,
            approval=action.approval,
            effect_status=action.effect_status,
            reason_code=action.reason_code,
        )
        for action in task.actions
    )


def _decisions(runtime: Runtime, task: Task, case: EvalCase, errors: list[str]) -> Task:
    for decision in case.decisions:
        if decision.op == "advance":
            runtime.clock.advance(decision.seconds)
            continue
        actor = Actor(decision.actor_id, decision.actor_role)
        try:
            if decision.op == "approve":
                task = runtime.approve(task.id, actor, decision.action, decision.record_id)
            elif decision.op == "reject":
                task = runtime.reject(task.id, actor, decision.action, decision.record_id)
            elif decision.op == "cancel":
                task = runtime.cancel(task.id, actor)
        except GateLabError as exc:
            if exc.reason_code != decision.expect_error:
                errors.append(f"{decision.op} {exc.reason_code}")
            continue
        if decision.expect_error:
            errors.append(f"missing {decision.expect_error}")
    return task


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _no_sleep(delay: float) -> None:
    del delay
