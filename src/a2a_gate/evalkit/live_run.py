"""Opt-in live eval. Only the planner talks to xAI.

Policy, approvals, the kill switch, the hash chain, idempotency, and the
invariant checks are the cassette runner. Human decisions stay scripted.
This module returns before constructing a socket unless ``LIVE_ENABLED=1``
and ``XAI_API_KEY`` are both set.
"""

from __future__ import annotations

import json
import random
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from a2a_gate.evalkit.action_view import (
    ActionFact,
    action_result,
    proposal_names,
    summarize_proposals,
)
from a2a_gate.evalkit.cases import EvalCase, load_cases
from a2a_gate.evalkit.suite import run_case
from a2a_gate.live import (
    ChatClient,
    LivePlanner,
    LiveSettings,
    Sleeper,
    SpendCap,
    Transport,
    urllib_transport,
)


@dataclass(frozen=True)
class LiveReport:
    text: str
    invariant_clean: int
    matched: int
    cases: int
    calls: int
    aborted: str


def live_cli(evals_dir: Path, out_dir: Path | None, label: str) -> int:
    settings = LiveSettings.from_env()
    if not settings.enabled:
        print("live: disabled. Set LIVE_ENABLED=1 to opt in. No request was sent.")
        return 2
    if settings.api_key == "":
        print("live: XAI_API_KEY is empty. No request was sent.")
        return 2
    destination = out_dir if out_dir is not None else Path("var") / "live" / label
    report = execute_live(
        evals_dir=evals_dir,
        out_dir=destination,
        settings=settings,
        transport=urllib_transport,
        label=label,
    )
    print(report.text)
    if report.aborted:
        return 1
    return 0


def execute_live(
    *,
    evals_dir: Path,
    out_dir: Path,
    settings: LiveSettings,
    transport: Transport,
    label: str,
    cases: tuple[EvalCase, ...] | None = None,
    sleeper: Sleeper | None = None,
    rng: random.Random | None = None,
) -> LiveReport:
    """Run cases with one shared live planner."""

    chosen = cases if cases is not None else load_cases(evals_dir / "cases.json")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = ChatClient(
        settings,
        transport,
        out_dir / "calls.jsonl",
        label,
        sleeper=sleeper,
        rng=rng,
    )
    planner = LivePlanner(client)
    rows: list[dict[str, object]] = []
    facts: list[ActionFact] = []
    aborted = ""
    for case in chosen:
        try:
            outcome = run_case(
                case,
                out_dir / "cases" / case.id,
                enforce_gate=True,
                planner=planner,
            )
        except SpendCap:
            aborted = "live_spend_cap"
            rows.append(_aborted_row(case, aborted))
            break
        client.attach_gate(case.id, proposal_names(outcome.actions), _results(outcome.actions))
        facts.extend(outcome.actions)
        rows.append(
            {
                "applied": outcome.applied,
                "case": case.id,
                "category": case.category,
                "duplicate_applied": outcome.duplicate_applied,
                "errors": list(outcome.errors),
                "expected_applied": case.expect_applied,
                "expected_state": case.expect_state,
                "invariants": list(outcome.invariants),
                "state": outcome.state,
            }
        )
    clean, matched, duplicates = _counts(rows)
    summary = _summary(label, rows, client.calls, aborted, clean, matched, duplicates)
    summary.update(summarize_proposals(facts))
    _write_json(out_dir / "results.json", rows)
    _write_json(out_dir / "summary.json", summary)
    text = _text(summary, clean, matched, duplicates)
    return LiveReport(
        text=text,
        invariant_clean=clean,
        matched=matched,
        cases=len(rows),
        calls=len(client.calls),
        aborted=aborted,
    )


def _aborted_row(case: EvalCase, reason: str) -> dict[str, object]:
    return {
        "applied": 0,
        "case": case.id,
        "category": case.category,
        "duplicate_applied": 0,
        "error": reason,
        "errors": [reason],
        "expected_applied": case.expect_applied,
        "expected_state": case.expect_state,
        "invariants": [],
        "state": "",
    }


def _counts(rows: list[dict[str, object]]) -> tuple[int, int, int]:
    clean = 0
    matched = 0
    duplicates = 0
    for row in rows:
        if row.get("error"):
            continue
        invariants = row.get("invariants")
        errors = row.get("errors")
        if invariants == []:
            clean += 1
        if invariants == [] and errors == []:
            matched += 1
        raw_dup = row.get("duplicate_applied")
        if isinstance(raw_dup, int) and not isinstance(raw_dup, bool):
            duplicates += raw_dup
    return clean, matched, duplicates


def _summary(
    label: str,
    rows: list[dict[str, object]],
    calls: list[dict[str, object]],
    aborted: str,
    clean: int,
    matched: int,
    duplicates: int,
) -> dict[str, object]:
    latencies: list[float] = []
    for item in calls:
        latency = _as_float(item.get("latency_s"))
        if latency is not None:
            latencies.append(latency)
    latencies.sort()
    ticks = 0
    for item in calls:
        raw = item.get("cost_in_usd_ticks")
        if isinstance(raw, int) and not isinstance(raw, bool):
            ticks += raw
    http: dict[str, int] = {}
    for status, count in Counter(item.get("http_status") for item in calls).items():
        http[str(status)] = count
    return {
        "aborted": aborted,
        "calls": len(calls),
        "cases": len(rows),
        "cost_usd": ticks / 10_000_000_000,
        "duplicate_applied": duplicates,
        "http": http,
        "invariant_clean": clean,
        "matched_expectations": matched,
        "p50": statistics.median(latencies) if latencies else None,
        "p95": _percentile(latencies, 0.95),
        "run": label,
        "tokens_in": _sum_int(calls, "tokens_in"),
        "tokens_out": _sum_int(calls, "tokens_out"),
    }


def _text(summary: dict[str, object], clean: int, matched: int, duplicates: int) -> str:
    aborted = summary["aborted"]
    stopped = isinstance(aborted, str) and aborted != ""
    return "\n".join(
        [
            "live planner: stopped" if stopped else "live planner: finished",
            f"run: {summary['run']}",
            f"cases: {summary['cases']}",
            f"calls: {summary['calls']}",
            f"invariant_clean: {clean}",
            f"matched_expectations: {matched}",
            f"duplicate_applied: {duplicates}",
            f"cost_usd: {summary['cost_usd']}",
            f"aborted: {aborted if stopped else 'no'}",
            _proposal_line(summary.get("proposals_by_action")),
            f"proposals_rejected: {summary.get('proposals_rejected', 0)}",
            f"proposals_approval_requested: {summary.get('proposals_approval_requested', 0)}",
            "proposals_unknown_or_out_of_policy: "
            f"{summary.get('proposals_unknown_or_out_of_policy', 0)}",
            "provider: xai",
            "approvals: scripted",
        ]
    )


def _results(facts: tuple[ActionFact, ...] | list[ActionFact]) -> list[dict[str, str]]:
    return [action_result(fact) for fact in facts]


def _proposal_line(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "proposals_by_action: none"
    parts: list[str] = []
    for key in sorted(value):
        if not isinstance(key, str):
            continue
        count = value[key]
        if isinstance(count, int) and not isinstance(count, bool):
            parts.append(f"{key}={count}")
    if not parts:
        return "proposals_by_action: none"
    return "proposals_by_action: " + ",".join(parts)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    k = (len(values) - 1) * fraction
    lower = int(k)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (k - lower)


def _sum_int(calls: list[dict[str, object]], field: str) -> int:
    total = 0
    for item in calls:
        raw = item.get(field)
        if isinstance(raw, int) and not isinstance(raw, bool):
            total += raw
    return total


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
