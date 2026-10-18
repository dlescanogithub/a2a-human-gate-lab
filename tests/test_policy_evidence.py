from pathlib import Path

import pytest

from a2a_gate.clock import ManualClock
from a2a_gate.errors import PermanentError, ValidationError
from a2a_gate.evidence import EvidenceLog, verify
from a2a_gate.policy import load_default_policy, load_policy_text


def test_policy_thresholds() -> None:
    policy = load_default_policy()
    assert policy.classify("read_record", 0) == "auto"
    assert policy.classify("draft_notice", 0) == "auto"
    assert policy.classify("issue_credit_note", 4999) == "auto"
    assert policy.classify("issue_credit_note", 5000) == "needs_approval"
    assert policy.classify("issue_credit_note", 500_000) == "needs_approval"
    assert policy.classify("issue_credit_note", 500_001) == "forbidden"
    assert policy.classify("issue_credit_note", 0) == "forbidden"
    assert policy.classify("change_supplier_bank", 0) == "needs_approval"
    assert policy.classify("send_customer_notice", 0) == "forbidden"
    assert policy.classify("procurement_exception", 0) == "forbidden"
    assert policy.classify("explode", 10) == "forbidden"
    assert "finance_approver" in policy.approver_roles
    assert policy.approval_ttl_seconds == 3600


def test_policy_yaml_rejects_unknown_shape() -> None:
    with pytest.raises(ValidationError):
        load_policy_text("approval_ttl_seconds: 10\n")
    with pytest.raises(ValidationError):
        load_policy_text("nope: 1\n")


def test_evidence_chain_and_tamper(tmp_path: Path) -> None:
    path = tmp_path / "evidence.jsonl"
    log = EvidenceLog(path, ManualClock())
    log.append("task_state", reason_code="ok", task_id="task_0001", note="do-not-keep")
    ok, detail = verify(path)
    assert ok
    assert "valid entries=1" == detail
    text = path.read_text(encoding="utf-8")
    assert "do-not-keep" not in text
    tampered = text.replace("task_0001", "task_9999")
    path.write_text(tampered, encoding="utf-8")
    ok, detail = verify(path)
    assert not ok
    assert "hash mismatch" in detail
    with pytest.raises(PermanentError):
        EvidenceLog(path, ManualClock())


def test_evidence_prev_mismatch_and_resume(tmp_path: Path) -> None:
    path = tmp_path / "evidence.jsonl"
    first = EvidenceLog(path, ManualClock())
    first.append("task_state", reason_code="ok")
    second = EvidenceLog(path, ManualClock())
    second.append("task_state", reason_code="replay")
    ok, detail = verify(path)
    assert ok
    assert detail.endswith("2")
    missing = tmp_path / "missing.jsonl"
    ok, detail = verify(missing)
    assert not ok
    assert detail == "missing"
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    ok, detail = verify(empty)
    assert ok
    assert detail == "empty"
    broken = tmp_path / "broken.jsonl"
    broken.write_text("{not json}\n", encoding="utf-8")
    ok, detail = verify(broken)
    assert not ok
    path.write_text(
        path.read_text(encoding="utf-8").replace("sha256:", "sha256:x", 1), encoding="utf-8"
    )
    ok, _detail = verify(path)
    assert not ok


def test_wall_clock_refuses_advance() -> None:
    from a2a_gate.clock import WallClock

    clock = WallClock()
    assert clock.time() > 0
    with pytest.raises(RuntimeError):
        clock.advance(1)
    manual = ManualClock()
    with pytest.raises(ValueError):
        manual.advance(-1)
