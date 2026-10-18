import http.client
import json
import random
import threading
from pathlib import Path

import pytest

from a2a_gate.catalog import INJECTION_NOTE, get_record, with_note
from a2a_gate.clock import ManualClock
from a2a_gate.config import Config
from a2a_gate.downstream import FakeDownstream, call_with_retries
from a2a_gate.errors import AuthError, TransientError, ValidationError
from a2a_gate.evidence import EvidenceLog
from a2a_gate.http_api import dispatch, make_server
from a2a_gate.planner import CassettePlanner, FakePlanner
from a2a_gate.policy import load_default_policy
from a2a_gate.runtime import Runtime
from a2a_gate.types import Actor, Plan, Proposal


def _runtime(tmp_path: Path, *, failures: int = 0, enforce: bool = True) -> Runtime:
    return Runtime(
        policy=load_default_policy(),
        evidence=EvidenceLog(tmp_path / "evidence.jsonl", ManualClock()),
        downstream=FakeDownstream(failures),
        clock=ManualClock(),
        planner=FakePlanner(),
        admin_token="lab-admin",
        enforce_gate=enforce,
        sleeper=lambda _delay: None,
        rng=random.Random(0),
    )


def test_fake_planner_ignores_note_text() -> None:
    planner = FakePlanner()
    plan = planner.complete(
        __import__("a2a_gate.types", fromlist=["PlanRequest"]).PlanRequest(
            message="leer el caso",
            record_id="INV-INJECT",
            case_id="x",
        )
    )
    assert [item.action for item in plan.proposals] == ["read_record"]
    injected = planner.complete(
        __import__("a2a_gate.types", fromlist=["PlanRequest"]).PlanRequest(
            message=INJECTION_NOTE,
            record_id="INV-INJECT",
            case_id="x",
        )
    )
    assert "change_supplier_bank" in [item.action for item in injected.proposals]


def test_cassette_exhausts(tmp_path: Path) -> None:
    plan = Plan("cassette", (Proposal("read_record", "INV-1001"),), 1, 1)
    planner = CassettePlanner(plan)
    runtime = _runtime(tmp_path)
    runtime.planner = planner
    task = runtime.create_task(Actor("requester.ana", "requester"), "leer", "INV-1001", "k1")
    assert task.state == "completed"
    with pytest.raises(Exception, match="cassette_exhausted"):
        planner.complete(
            __import__("a2a_gate.types", fromlist=["PlanRequest"]).PlanRequest(
                "leer", "INV-1001", "x"
            )
        )


def test_gate_kill_idempotency_and_retries(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    requester = Actor("requester.ana", "requester")
    approver = Actor("approver.finance", "finance_approver")
    pending = runtime.create_task(requester, "nota de credito", "INV-1001", "credit")
    assert pending.state == "input-required"
    with pytest.raises(AuthError):
        runtime.approve(pending.id, requester, "issue_credit_note", "INV-1001")
    with pytest.raises(AuthError):
        runtime.approve(
            pending.id,
            Actor("approver.newbie", "requester"),
            "issue_credit_note",
            "INV-1001",
        )
    approved = runtime.approve(pending.id, approver, "issue_credit_note", "INV-1001")
    assert approved.state == "completed"
    again = runtime.approve(pending.id, approver, "issue_credit_note", "INV-1001")
    assert again.state == "completed"
    assert runtime.downstream.applied == ["credit:issue_credit_note:INV-1001"]
    replay = runtime.create_task(requester, "nota de credito", "INV-1001", "credit")
    assert replay.id == pending.id

    bank = runtime.create_task(requester, "cambiar banco", "SUP-2001", "bank")
    rejected = runtime.reject(bank.id, approver, "change_supplier_bank", "SUP-2001")
    assert rejected.state == "rejected"
    still = runtime.approve(bank.id, approver, "change_supplier_bank", "SUP-2001")
    assert still.state == "rejected"
    assert len(runtime.downstream.applied) == 1

    runtime.clock.advance(10)
    waiting = runtime.create_task(requester, "nota de credito", "INV-1005", "ttl")
    runtime.clock.advance(3600)
    expired = runtime.approve(waiting.id, approver, "issue_credit_note", "INV-1005")
    assert expired.state == "rejected"

    runtime.kill("lab-admin", Actor("admin.ops", "admin"))
    blocked = runtime.create_task(requester, "nota de credito", "INV-1002", "after")
    assert blocked.state == "failed"
    assert len(runtime.downstream.applied) == 1
    with pytest.raises(AuthError):
        runtime.kill("nope", Actor("admin.ops", "admin"))
    with pytest.raises(AuthError):
        runtime.kill("lab-admin", Actor("approver.finance", "finance_approver"))


def test_dead_letter_and_validation(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, failures=5)
    task = runtime.create_task(
        Actor("requester.ana", "requester"), "nota de credito", "INV-1002", "dead"
    )
    assert task.state == "failed"
    assert task.actions[0].attempts == 3
    assert runtime.downstream.applied == []
    with pytest.raises(ValidationError):
        runtime.create_task(Actor("requester.ana", "requester"), "leer", "INV-1001", "")
    missing = runtime.create_task(
        Actor("requester.ana", "requester"), "leer", "INV-MISSING", "missing"
    )
    assert missing.state == "failed"
    with pytest.raises(ValidationError):
        runtime.snapshot("nope")
    record = get_record("INV-1001")
    assert record is not None
    with pytest.raises(ValidationError):
        runtime.create_task(
            Actor("requester.ana", "requester"),
            "leer",
            "INV-1002",
            "mismatch",
            record=with_note(record, "otra"),
        )


def test_admin_can_approve_and_cancel(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    requester = Actor("requester.ana", "requester")
    task = runtime.create_task(requester, "nota de credito", "INV-1001", "admin-ok")
    approved = runtime.approve(
        task.id, Actor("admin.ops", "admin"), "issue_credit_note", "INV-1001"
    )
    assert approved.state == "completed"
    read = runtime.create_task(requester, "leer factura", "INV-1001", "read")
    canceled = runtime.cancel(read.id, requester)
    assert canceled.state == "completed"
    pending = runtime.create_task(requester, "cambiar banco", "SUP-2001", "pend")
    with pytest.raises(AuthError):
        runtime.cancel(pending.id, Actor("other.person", "requester"))
    stopped = runtime.cancel(pending.id, Actor("admin.ops", "admin"))
    assert stopped.state == "canceled"


def test_bypass_applies_without_approval(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, enforce=False)
    task = runtime.create_task(
        Actor("requester.ana", "requester"), "nota de credito", "INV-1001", "bypass"
    )
    assert task.state == "completed"
    assert task.actions[0].approval == "not_required"
    assert task.actions[0].effect_status == "applied"


def test_retry_delay_is_bounded() -> None:
    downstream = FakeDownstream(2)
    delays: list[float] = []
    result = call_with_retries(
        downstream,
        "key",
        max_attempts=3,
        rng=random.Random(0),
        sleeper=delays.append,
    )
    assert result.status == "applied"
    assert result.attempts == 3
    assert delays
    assert max(delays) <= 8
    with pytest.raises(ValueError):
        call_with_retries(
            downstream, "key", max_attempts=0, rng=random.Random(0), sleeper=delays.append
        )


def test_downstream_rejects_negative() -> None:
    with pytest.raises(ValueError):
        FakeDownstream(-1)
    boom = FakeDownstream(1)

    def _raise(key: str) -> None:
        del key
        raise TransientError("downstream_unavailable")

    boom.apply = _raise  # type: ignore[method-assign]
    result = call_with_retries(
        boom, "key", max_attempts=1, rng=random.Random(0), sleeper=lambda _delay: None
    )
    assert result.status == "dead_letter"


def test_http_dispatch_and_server(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    base = "http://127.0.0.1:8765"
    health, body = dispatch("GET", "/health", {}, b"", runtime, "lab-api", base)
    assert health == 200
    assert body["status"] == "ok"
    status, card = dispatch(
        "GET", "/.well-known/agent-card.json", {}, b"", runtime, "lab-api", base
    )
    assert status == 200
    assert card["signatures"] == []
    assert card["labNotice"]
    denied, _payload = dispatch("POST", "/v1/tasks", {}, b"{}", runtime, "lab-api", base)
    assert denied == 401
    created, task = dispatch(
        "POST",
        "/v1/tasks",
        {"Authorization": "Bearer lab-api"},
        json.dumps(
            {
                "requester_id": "requester.ana",
                "requester_role": "requester",
                "message": "nota de credito",
                "record_id": "INV-1001",
                "idempotency_key": "http-1",
            }
        ).encode(),
        runtime,
        "lab-api",
        base,
    )
    assert created == 200
    task_id = task["id"]
    assert isinstance(task_id, str)
    fetched, got = dispatch(
        "GET",
        f"/v1/tasks/{task_id}",
        {"authorization": "Bearer lab-api"},
        b"",
        runtime,
        "lab-api",
        base,
    )
    assert fetched == 200
    assert got["id"] == task_id
    missing, err = dispatch(
        "GET",
        "/v1/tasks/missing",
        {"Authorization": "Bearer lab-api"},
        b"",
        runtime,
        "lab-api",
        base,
    )
    assert missing == 404
    assert err["error"] == "unknown_task"
    bad, err = dispatch(
        "POST",
        "/v1/tasks",
        {"Authorization": "Bearer lab-api"},
        b"{",
        runtime,
        "lab-api",
        base,
    )
    assert bad == 400
    killed, body = dispatch(
        "POST",
        "/v1/admin/kill-switch",
        {"Authorization": "Bearer lab-api", "X-Admin-Token": "lab-admin"},
        json.dumps({"actor_id": "admin.ops", "actor_role": "admin"}).encode(),
        runtime,
        "lab-api",
        base,
    )
    assert killed == 200
    assert body["killed"] is True
    verify_status, verified = dispatch(
        "GET",
        "/v1/evidence/verify",
        {"Authorization": "Bearer lab-api"},
        b"",
        runtime,
        "lab-api",
        base,
    )
    assert verify_status == 200
    assert verified["ok"] is True
    unknown, _payload = dispatch(
        "GET",
        "/nope",
        {"Authorization": "Bearer lab-api"},
        b"",
        runtime,
        "lab-api",
        base,
    )
    assert unknown == 404

    config = Config(
        host="127.0.0.1",
        port=0,
        public_base_url=base,
        api_token="lab-api",
        admin_token="lab-admin",
        evidence_path=tmp_path / "evidence.jsonl",
        log_level="INFO",
        llm_provider="fake",
        llm_api_key="",
        llm_base_url="",
        llm_model="",
        live_mode=False,
        max_attempts=3,
        seed=1,
    )
    server = make_server(config, runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        connection = http.client.HTTPConnection(str(host), int(port), timeout=5)
        connection.request("GET", "/health")
        response = connection.getresponse()
        assert response.status == 200
        connection.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
