"""Append-only hash-chained JSONL.

Each line includes the previous line's hash. ``verify`` recomputes the chain.
Fields are an allowlist: customer notes, emails, and account numbers are not
fields, so they cannot be written by accident through ``append``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from pathlib import Path
from typing import cast

from a2a_gate.clock import Clock
from a2a_gate.errors import PermanentError

GENESIS = "sha256:" + ("0" * 64)

ALLOWED: frozenset[str] = frozenset(
    {
        "task_id",
        "action",
        "record_id",
        "actor_id",
        "actor_role",
        "amount_cents",
        "disposition",
        "approval",
        "effect_status",
        "attempts",
        "reason_code",
        "tokens_in",
        "tokens_out",
        "proposal_count",
        "ignored_claims",
    }
)


def chain_hash(prev: str, body: dict[str, object]) -> str:
    payload = dict(body)
    payload["prev"] = prev
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class EvidenceLog:
    def __init__(self, path: Path, clock: Clock) -> None:
        self.path = path
        self.clock = clock
        self._lock = threading.Lock()
        self._seq = 0
        self._prev = GENESIS
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        elif path.read_text(encoding="utf-8").strip():
            ok, _detail = verify(path)
            if not ok:
                raise PermanentError("evidence_tampered")
            self._resume(path)

    def append(self, event: str, **fields: object) -> dict[str, object]:
        with self._lock:
            body: dict[str, object] = {
                "event": event,
                "seq": self._seq + 1,
                "ts": self.clock.time(),
            }
            for key in sorted(ALLOWED):
                if key in fields:
                    body[key] = fields[key]
            digest = chain_hash(self._prev, body)
            record: dict[str, object] = dict(body)
            record["prev"] = self._prev
            record["hash"] = digest
            line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            self._seq += 1
            self._prev = digest
            return record

    def _resume(self, path: Path) -> None:
        last = ""
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = line
                count += 1
        parsed = json.loads(last)
        if not isinstance(parsed, dict):
            raise PermanentError("evidence_tampered")
        prev = parsed.get("hash")
        if not isinstance(prev, str):
            raise PermanentError("evidence_tampered")
        self._prev = prev
        self._seq = count


def verify(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    text = path.read_text(encoding="utf-8")
    if text.strip() == "":
        return True, "empty"
    prev = GENESIS
    count = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return False, f"line {line_no} invalid json"
        if not isinstance(parsed, dict):
            return False, f"line {line_no} not an object"
        record: dict[str, object] = {}
        for key, value in parsed.items():
            if not isinstance(key, str):
                return False, f"line {line_no} bad key"
            record[key] = cast(object, value)
        claimed = record.pop("hash", None)
        claimed_prev = record.get("prev")
        if claimed_prev != prev or not isinstance(claimed, str):
            return False, f"line {line_no} prev mismatch"
        body = dict(record)
        body.pop("prev", None)
        expect = chain_hash(prev, body)
        try:
            match = hmac.compare_digest(expect, claimed)
        except (TypeError, ValueError):
            match = False
        if not match:
            return False, f"line {line_no} hash mismatch"
        prev = claimed
        count += 1
    return True, f"valid entries={count}"
