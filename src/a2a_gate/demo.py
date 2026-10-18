"""One-command walkthrough. Fake planner, no network, tokens generated here."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from a2a_gate.clock import ManualClock
from a2a_gate.config import Config
from a2a_gate.evidence import verify
from a2a_gate.http_api import dispatch
from a2a_gate.runtime import Runtime
from a2a_gate.wiring import build_runtime


def run_demo(evidence_path: Path) -> tuple[int, list[str]]:
    api_token = secrets.token_hex(16)
    admin_token = secrets.token_hex(16)
    base_url = "http://127.0.0.1:8765"
    config = Config(
        host="127.0.0.1",
        port=8765,
        public_base_url=base_url,
        api_token=api_token,
        admin_token=admin_token,
        evidence_path=evidence_path,
        log_level="INFO",
        llm_provider="fake",
        llm_api_key="",
        llm_base_url="",
        llm_model="",
        live_mode=False,
        max_attempts=3,
        seed=42,
    )
    runtime = build_runtime(
        config,
        clock=ManualClock(),
        evidence_path=evidence_path,
        sleeper=_no_sleep,
    )
    lines = [
        "lab: fake provider, no network",
        "notice: in-process tokens are NOT REAL and are not stored",
    ]
    code = 0
    status, card = dispatch(
        "GET", "/.well-known/agent-card.json", {}, b"", runtime, api_token, base_url
    )
    name = card.get("name")
    lines.append(f"card: {name if isinstance(name, str) else 'missing'}")
    if status != 200 or name != "Nube Austral Back Office":
        return 1, lines + ["demo mismatch: card"]

    _read, code = _expect(
        lines,
        code,
        "read",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            "/v1/tasks",
            _task("leer factura", "INV-1001", "demo-read"),
        ),
        200,
        "completed",
    )
    credit, code = _expect(
        lines,
        code,
        "credit pending",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            "/v1/tasks",
            _task("nota de credito", "INV-1001", "demo-credit"),
        ),
        200,
        "input-required",
    )
    denied_status, denied = _send(
        runtime,
        api_token,
        base_url,
        "POST",
        f"/v1/tasks/{_task_id(credit)}:approve",
        _decision("requester.ana", "finance_approver", "issue_credit_note", "INV-1001"),
    )
    if denied_status == 403 and denied.get("error") == "self_approval":
        lines.append("self-approval: denied")
    else:
        lines.append("demo mismatch: self-approval")
        code = 1
    _approved, code = _expect(
        lines,
        code,
        "credit approved",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            f"/v1/tasks/{_task_id(credit)}:approve",
            _decision("approver.finance", "finance_approver", "issue_credit_note", "INV-1001"),
        ),
        200,
        "completed",
    )
    _replay, code = _expect(
        lines,
        code,
        "credit replay",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            f"/v1/tasks/{_task_id(credit)}:approve",
            _decision("approver.finance", "finance_approver", "issue_credit_note", "INV-1001"),
        ),
        200,
        "completed",
    )
    bank, code = _expect(
        lines,
        code,
        "bank pending",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            "/v1/tasks",
            _task("cambiar banco", "SUP-2001", "demo-bank"),
        ),
        200,
        "input-required",
    )
    _rejected, code = _expect(
        lines,
        code,
        "bank rejected",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            f"/v1/tasks/{_task_id(bank)}:reject",
            _decision("approver.finance", "finance_approver", "change_supplier_bank", "SUP-2001"),
        ),
        200,
        "rejected",
    )
    _bank_replay, code = _expect(
        lines,
        code,
        "bank replay",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            "/v1/tasks",
            _task("cambiar banco", "SUP-2001", "demo-bank"),
        ),
        200,
        "rejected",
    )
    kill_status, kill_body = _send(
        runtime,
        api_token,
        base_url,
        "POST",
        "/v1/admin/kill-switch",
        {"actor_id": "admin.ops", "actor_role": "admin"},
        admin_token=admin_token,
    )
    if kill_status == 200 and kill_body.get("killed") is True:
        lines.append("kill switch: halted")
    else:
        lines.append("demo mismatch: kill switch")
        code = 1
    _blocked, code = _expect(
        lines,
        code,
        "after kill",
        _send(
            runtime,
            api_token,
            base_url,
            "POST",
            "/v1/tasks",
            _task("nota de credito", "INV-1002", "demo-after-kill"),
        ),
        200,
        "failed",
    )
    applied = len(runtime.downstream.applied)
    lines.append(f"applied effects: {applied}")
    if applied != 1:
        lines.append("demo mismatch: applied effects")
        code = 1
    ok, detail = verify(evidence_path)
    lines.append(f"evidence: {detail if ok else 'invalid'}")
    if not ok:
        lines.append("demo mismatch: evidence")
        code = 1
    return code, lines


def _task(message: str, record_id: str, idempotency_key: str) -> dict[str, object]:
    return {
        "requester_id": "requester.ana",
        "requester_role": "requester",
        "message": message,
        "record_id": record_id,
        "idempotency_key": idempotency_key,
    }


def _decision(actor_id: str, role: str, action: str, record_id: str) -> dict[str, object]:
    return {
        "actor_id": actor_id,
        "actor_role": role,
        "action": action,
        "record_id": record_id,
    }


def _send(
    runtime: Runtime,
    api_token: str,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, object],
    admin_token: str = "",
) -> tuple[int, dict[str, object]]:
    headers = {"Authorization": "Bearer " + api_token}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    body = json.dumps(payload).encode("utf-8")
    return dispatch(method, path, headers, body, runtime, api_token, base_url)


def _expect(
    lines: list[str],
    code: int,
    label: str,
    result: tuple[int, dict[str, object]],
    status: int,
    state: str,
) -> tuple[dict[str, object], int]:
    got_status, payload = result
    actual = _state(payload)
    lines.append(f"{label}: {actual or got_status}")
    if got_status != status or actual != state:
        lines.append(f"demo mismatch: {label}")
        return payload, 1
    return payload, code


def _state(payload: dict[str, object]) -> str:
    status = payload.get("status")
    if not isinstance(status, dict):
        return ""
    state = status.get("state")
    if not isinstance(state, str):
        return ""
    return state


def _task_id(payload: dict[str, object]) -> str:
    value = payload.get("id")
    if not isinstance(value, str) or value == "":
        return "missing"
    return value


def _no_sleep(delay: float) -> None:
    del delay
