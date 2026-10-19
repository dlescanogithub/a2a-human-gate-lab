"""Offline tests for the optional xAI planner. No test opens a socket."""

from __future__ import annotations

import io
import json
import logging
import random
from dataclasses import replace
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from a2a_gate.catalog import INJECTION_NOTE
from a2a_gate.errors import ConfigError, PermanentError, TransientError
from a2a_gate.evalkit.__main__ import main
from a2a_gate.evalkit.action_view import ActionFact, action_result
from a2a_gate.evalkit.cases import Decision, EvalCase, load_cases
from a2a_gate.evalkit.live_run import execute_live
from a2a_gate.evalkit.suite import run_case
from a2a_gate.live import (
    DEFAULT_CAP_USD,
    DEFAULT_MODEL,
    ChatClient,
    HttpResponse,
    LivePlanner,
    LiveSettings,
    SpendCap,
    parse_proposals,
    urllib_transport,
)
from a2a_gate.logging_setup import JsonFormatter
from a2a_gate.types import Plan, PlanRequest

ROOT = Path(__file__).resolve().parents[1]


def _key() -> str:
    return ("xa" + "i-") + ("k" * 24)


def _settings(**overrides: object) -> LiveSettings:
    settings = LiveSettings(
        enabled=True,
        api_key=_key(),
        base_url="http://127.0.0.1:9/v1/chat/completions",
        model=DEFAULT_MODEL,
        max_spend_usd=DEFAULT_CAP_USD,
        max_tokens=300,
        max_attempts=3,
        timeout_s=5.0,
        input_usd_per_mtok=3.0,
        cached_usd_per_mtok=0.75,
        output_usd_per_mtok=15.0,
        price_as_of="2026-10-18",
    )
    if not overrides:
        return settings
    return replace(settings, **overrides)  # type: ignore[arg-type]


class FakeTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = responses
        self.bodies: list[bytes] = []
        self.headers: list[dict[str, str]] = []

    def __call__(
        self, url: str, body: bytes, headers: dict[str, str], timeout_s: float
    ) -> HttpResponse:
        del url, timeout_s
        self.bodies.append(body)
        self.headers.append(dict(headers))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def _body(
    content: str | None,
    *,
    ticks: int | None = 1000,
    prompt: int = 10,
    completion: int = 4,
    cached: int = 2,
    choices: bool = True,
) -> bytes:
    usage: dict[str, object] = {
        "completion_tokens": completion,
        "prompt_tokens": prompt,
        "prompt_tokens_details": {"cached_tokens": cached},
    }
    if ticks is not None:
        usage["cost_in_usd_ticks"] = ticks
    payload: dict[str, object] = {"usage": usage}
    if choices:
        payload["choices"] = [{"message": {"content": content}}]
    return json.dumps(payload).encode("utf-8")


def _client(
    transport: FakeTransport,
    log_path: Path,
    settings: LiveSettings | None = None,
    sleeper: list[float] | None = None,
) -> ChatClient:
    delays = sleeper if sleeper is not None else []
    return ChatClient(
        settings or _settings(),
        transport,
        log_path,
        "unit",
        sleeper=delays.append,
        rng=random.Random(0),
    )


def _case(case_id: str) -> EvalCase:
    return next(case for case in load_cases(ROOT / "evals" / "cases.json") if case.id == case_id)


def test_missing_key_sends_nothing(tmp_path: Path) -> None:
    transport = FakeTransport([])
    client = _client(transport, tmp_path / "calls.jsonl", _settings(api_key=""))
    with pytest.raises(ConfigError) as caught:
        client.chat(({"role": "user", "content": "hola"},), case_id="hp_read")
    assert caught.value.reason_code == "live_key_missing"
    assert transport.bodies == []
    assert not (tmp_path / "calls.jsonl").exists()


def test_spend_cap_stops_before_the_next_request(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            HttpResponse(200, _body('{"proposals":[]}', ticks=1_000_000)),
            HttpResponse(200, _body('{"proposals":[]}', ticks=1)),
        ]
    )
    client = _client(
        transport,
        tmp_path / "calls.jsonl",
        _settings(max_spend_usd=0.0001),
    )
    client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    with pytest.raises(SpendCap):
        client.chat(({"role": "user", "content": "two"},), case_id="hp_draft")
    assert len(transport.bodies) == 1


def test_zero_cap_sends_nothing(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(200, _body('{"proposals":[]}'))])
    client = _client(transport, tmp_path / "calls.jsonl", _settings(max_spend_usd=0.0))
    with pytest.raises(SpendCap):
        client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert transport.bodies == []


def test_http_400_is_not_retried(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(400, b"no")])
    delays: list[float] = []
    client = _client(transport, tmp_path / "calls.jsonl", sleeper=delays)
    with pytest.raises(PermanentError):
        client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert len(transport.bodies) == 1
    assert delays == []
    text = (tmp_path / "calls.jsonl").read_text(encoding="utf-8")
    assert "no" not in text
    assert '"http_status": 400' in text


def test_http_500_retries_then_succeeds(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            HttpResponse(500, b"later", retry_after_s=0.25),
            HttpResponse(200, _body('{"proposals":[]}', ticks=50)),
        ]
    )
    delays: list[float] = []
    client = _client(transport, tmp_path / "calls.jsonl", sleeper=delays)
    reply = client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert reply.cost_ticks == 50
    assert reply.cost_source == "ticks"
    assert len(transport.bodies) == 2
    assert delays == [0.25]
    lines = (tmp_path / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "later" not in "\n".join(lines)


def test_http_500_stops_after_the_attempt_cap(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(503, b"down") for _ in range(3)])
    delays: list[float] = []
    client = _client(transport, tmp_path / "calls.jsonl", sleeper=delays)
    with pytest.raises(TransientError):
        client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert len(transport.bodies) == 3
    assert len(delays) == 2


def test_transport_exception_is_retried_without_logging_the_message(tmp_path: Path) -> None:
    class Exploding:
        def __call__(
            self, url: str, body: bytes, headers: dict[str, str], timeout_s: float
        ) -> HttpResponse:
            del url, body, headers, timeout_s
            raise OSError("no-socket-detail")

    delays: list[float] = []
    client = ChatClient(
        _settings(max_attempts=2),
        Exploding(),
        tmp_path / "calls.jsonl",
        "unit",
        sleeper=delays.append,
    )
    with pytest.raises(TransientError):
        client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    text = (tmp_path / "calls.jsonl").read_text(encoding="utf-8")
    assert "no-socket-detail" not in text
    assert '"error": "live_transport"' in text
    assert len(delays) == 1


def test_key_prompt_and_note_stay_out_of_logs(tmp_path: Path) -> None:
    content = json.dumps({"proposals": [{"action": "read_record", "record_id": "INV-1001"}]})
    transport = FakeTransport([HttpResponse(200, _body(content, ticks=1230500))])
    log_path = tmp_path / "calls.jsonl"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("a2a_gate.live")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        planner = LivePlanner(_client(transport, log_path))
        plan = planner.complete(PlanRequest("leer factura", "INV-1001", "hp_read"))
    finally:
        logger.removeHandler(handler)
    assert plan.proposals[0].action == "read_record"
    assert plan.tokens_in == 10
    raw = log_path.read_text(encoding="utf-8")
    logged = raw + stream.getvalue()
    assert _key() not in logged
    assert "Bearer" not in logged
    assert "pago duplicado" not in logged
    assert "fictional company" not in logged
    assert "leer factura" not in logged
    assert b"pago duplicado" in transport.bodies[0]
    assert _key().encode() not in transport.bodies[0]
    assert transport.headers[0]["Authorization"] == "Bearer " + _key()


def test_parse_fenced_json_and_empty_list() -> None:
    fenced = '```json\n{"proposals":[{"action":"draft_notice","record_id":"INV-1001"}]}\n```'
    proposals = parse_proposals(fenced, "INV-1001")
    assert proposals[0].action == "draft_notice"
    assert parse_proposals('{"proposals":[]}', "INV-1001") == ()
    missing = parse_proposals('{"proposals":[{"action":"read_record"}]}', "INV-1002")
    assert missing[0].record_id == "INV-1002"
    with pytest.raises(PermanentError):
        parse_proposals("not json", "INV-1001")
    with pytest.raises(PermanentError):
        parse_proposals('{"proposals":[{"action":""}]}', "INV-1001")


def test_ticks_win_over_the_dated_fallback(tmp_path: Path) -> None:
    transport = FakeTransport(
        [HttpResponse(200, _body('{"proposals":[]}', ticks=1230500, prompt=1000, cached=200))]
    )
    client = _client(transport, tmp_path / "calls.jsonl")
    reply = client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert reply.cost_source == "ticks"
    assert reply.cost_ticks == 1230500
    assert client.spent_ticks == 1230500


def test_fallback_price_is_dated_and_used_when_ticks_are_absent(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            HttpResponse(
                200,
                _body('{"proposals":[]}', ticks=None, prompt=1000, completion=10, cached=200),
            )
        ]
    )
    settings = _settings()
    client = _client(transport, tmp_path / "calls.jsonl", settings)
    reply = client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert settings.price_as_of == "2026-10-18"
    assert reply.cost_source == "fallback"
    assert reply.cost_ticks == 27_000_000
    parsed_line = json.loads((tmp_path / "calls.jsonl").read_text(encoding="utf-8"))
    assert parsed_line["cost_source"] == "fallback"
    assert parsed_line["cost_usd"] == 0.0027


def test_bad_body_still_counts_ticks_when_usage_is_present(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(200, _body(None, ticks=9, choices=False))])
    client = _client(transport, tmp_path / "calls.jsonl")
    with pytest.raises(PermanentError):
        client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert client.spent_ticks == 9
    text = (tmp_path / "calls.jsonl").read_text(encoding="utf-8")
    assert "live_bad_response" in text
    assert _key() not in text


def test_unparseable_plan(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(200, _body("hello there", ticks=3))])
    planner = LivePlanner(_client(transport, tmp_path / "calls.jsonl"))
    with pytest.raises(PermanentError) as caught:
        planner.complete(PlanRequest("leer", "INV-1001", "hp_read"))
    assert caught.value.reason_code == "live_unparseable_plan"


def test_settings_from_env_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LIVE_ENABLED",
        "XAI_API_KEY",
        "XAI_BASE_URL",
        "XAI_MODEL",
        "MAX_LIVE_SPEND_USD",
        "XAI_PRICE_AS_OF",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = LiveSettings.from_env()
    assert not settings.enabled
    assert settings.api_key == ""
    assert settings.model == DEFAULT_MODEL
    assert settings.max_spend_usd == DEFAULT_CAP_USD
    assert settings.price_as_of == "2026-10-18"
    monkeypatch.setenv("LIVE_ENABLED", "true")
    assert not LiveSettings.from_env().enabled
    monkeypatch.setenv("LIVE_ENABLED", "1")
    monkeypatch.setenv("XAI_MODEL", "lab-model")
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "0.25")
    turned_on = LiveSettings.from_env()
    assert turned_on.enabled
    assert turned_on.model == "lab-model"
    assert turned_on.max_spend_usd == 0.25
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "nope")
    with pytest.raises(ConfigError):
        LiveSettings.from_env()
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "0.1")
    monkeypatch.setenv("XAI_MAX_ATTEMPTS", "0")
    with pytest.raises(ConfigError):
        LiveSettings.from_env()
    monkeypatch.setenv("XAI_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "nan")
    with pytest.raises(ConfigError):
        LiveSettings.from_env()
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "inf")
    with pytest.raises(ConfigError):
        LiveSettings.from_env()
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "0.1")
    monkeypatch.setenv("XAI_MAX_TOKENS", "nope")
    with pytest.raises(ConfigError):
        LiveSettings.from_env()


def test_live_command_stays_offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def explode(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network")

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", explode)
    monkeypatch.delenv("LIVE_ENABLED", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    assert main(["live", "--out", str(tmp_path / "off")]) == 2
    monkeypatch.setenv("LIVE_ENABLED", "1")
    assert main(["live", "--out", str(tmp_path / "nokey")]) == 2
    monkeypatch.setenv("XAI_API_KEY", _key())
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "-5")
    assert main(["live", "--out", str(tmp_path / "bad")]) == 2
    assert not (tmp_path / "off").exists()
    assert not (tmp_path / "nokey").exists()


def test_enabled_command_uses_the_fake_transport(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[int] = []

    def fake(url: str, body: bytes, headers: dict[str, str], timeout_s: float) -> HttpResponse:
        del url, body, headers, timeout_s
        calls.append(1)
        plan = json.dumps({"proposals": [{"action": "read_record", "record_id": "INV-1001"}]})
        return HttpResponse(200, _body(plan, ticks=10))

    def explode(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network")

    monkeypatch.setattr("a2a_gate.evalkit.live_run.urllib_transport", fake)
    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", explode)
    monkeypatch.setenv("LIVE_ENABLED", "1")
    monkeypatch.setenv("XAI_API_KEY", _key())
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "0.10")
    code = main(
        ["live", "--out", str(tmp_path / "out"), "--label", "unit", "--evals", str(ROOT / "evals")]
    )
    assert code == 0
    assert len(calls) == 35
    text = (tmp_path / "out" / "calls.jsonl").read_text(encoding="utf-8")
    assert _key() not in text
    assert "fictional company" not in text
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "0")
    assert (
        main(
            [
                "live",
                "--out",
                str(tmp_path / "capped"),
                "--label",
                "capped",
                "--evals",
                str(ROOT / "evals"),
            ]
        )
        == 1
    )
    assert len(calls) == 35


def test_refuses_to_write_a_log_line_that_contains_the_key(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(200, _body('{"proposals":[]}'))])
    client = _client(transport, tmp_path / "calls.jsonl")
    with pytest.raises(PermanentError) as caught:
        client.chat(({"role": "user", "content": "one"},), case_id=_key())
    assert caught.value.reason_code == "live_log_refused"
    assert not (tmp_path / "calls.jsonl").exists()


def test_malformed_model_payloads(tmp_path: Path) -> None:
    bad_bodies = [
        b"\xff",
        b"[]",
        json.dumps({"choices": [{"message": {"content": 1}}]}).encode(),
        json.dumps({"choices": ["nope"]}).encode(),
        json.dumps({"choices": [{"message": None}]}).encode(),
    ]
    for sample in bad_bodies:
        transport = FakeTransport([HttpResponse(200, sample)])
        client = _client(transport, tmp_path / "calls.jsonl")
        with pytest.raises(PermanentError):
            client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    negative = json.dumps(
        {
            "choices": [{"message": {"content": '{"proposals":[]}'}}],
            "usage": {
                "completion_tokens": -1,
                "cost_in_usd_ticks": -5,
                "prompt_tokens": 0,
                "prompt_tokens_details": ["nope"],
            },
        }
    ).encode()
    client = _client(FakeTransport([HttpResponse(200, negative)]), tmp_path / "fallback.jsonl")
    reply = client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert reply.cost_source == "fallback"
    assert reply.cost_ticks == 0
    with pytest.raises(PermanentError):
        parse_proposals('{"proposals":"no"}', "INV-9")
    with pytest.raises(PermanentError):
        parse_proposals('{"proposals":["x"]}', "INV-9")
    blank = parse_proposals(
        '{"proposals":[{"action":"read_record","record_id":""}]}',
        "INV-9",
    )
    assert blank[0].record_id == "INV-9"


def test_planner_marks_a_missing_record(tmp_path: Path) -> None:
    content = json.dumps({"proposals": []})
    transport = FakeTransport([HttpResponse(200, _body(content, ticks=1))])
    planner = LivePlanner(_client(transport, tmp_path / "calls.jsonl"))
    plan = planner.complete(PlanRequest("leer", "NO-SUCH", "edge_unknown_record"))
    assert plan.proposals == ()
    assert b"missing" in transport.bodies[0]
    assert b"NO-SUCH" in transport.bodies[0]


def test_execute_live_uses_the_gate_and_stops_on_the_cap(tmp_path: Path) -> None:
    read = _case("hp_read")
    draft = _case("hp_draft")
    missing = _case("edge_missing_idempotency")
    plan = json.dumps(
        {
            "proposals": [
                {"action": item.action, "record_id": item.record_id} for item in read.proposals
            ]
        }
    )
    transport = FakeTransport(
        [
            HttpResponse(200, _body(plan, ticks=1_000_000, prompt=20, completion=5, cached=0)),
            HttpResponse(200, _body(plan, ticks=1)),
        ]
    )
    report = execute_live(
        evals_dir=ROOT / "evals",
        out_dir=tmp_path / "run",
        settings=_settings(max_spend_usd=0.0001),
        transport=transport,
        label="unit",
        cases=(missing, read, draft),
        sleeper=lambda delay: None,
    )
    assert report.aborted == "live_spend_cap"
    assert report.calls == 1
    assert len(transport.bodies) == 1
    assert report.invariant_clean == 2
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert summary["duplicate_applied"] == 0
    assert summary["cost_usd"] == 0.0001
    assert _key() not in (tmp_path / "run" / "calls.jsonl").read_text(encoding="utf-8")
    assert "pago duplicado" not in (tmp_path / "run" / "results.json").read_text(encoding="utf-8")


def test_injected_planner_replaces_the_cassette(tmp_path: Path) -> None:
    case = _case("hp_credit_auto")

    class Empty:
        def complete(self, request: PlanRequest) -> Plan:
            del request
            return Plan(content="empty", proposals=(), tokens_in=0, tokens_out=0)

    outcome = run_case(case, tmp_path / "case", enforce_gate=True, planner=Empty())
    assert outcome.errors
    assert outcome.duplicate_applied == 0
    cassette = run_case(case, tmp_path / "cassette", enforce_gate=True)
    assert cassette.ok


def test_urllib_transport_with_a_fake_opener(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Response:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def close(self) -> None:
            return None

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", lambda *_a, **_k: _Response())
    ok = urllib_transport("http://127.0.0.1:9/v1", b"{}", {}, 1.0)
    assert ok.status == 200
    assert ok.body == b"{}"

    headers = Message()
    headers["Retry-After"] = "1.5"
    error = HTTPError("http://127.0.0.1:9/v1", 429, "later", headers, io.BytesIO(b"quiet"))

    def raise_http(*_args: object, **_kwargs: object) -> object:
        raise error

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", raise_http)
    limited = urllib_transport("http://127.0.0.1:9/v1", b"{}", {}, 1.0)
    assert limited.status == 429
    assert limited.retry_after_s == 1.5
    assert limited.body == b"quiet"

    def raise_url(*_args: object, **_kwargs: object) -> object:
        raise URLError("down")

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", raise_url)
    failed = urllib_transport("http://127.0.0.1:9/v1", b"{}", {}, 1.0)
    assert failed.status == 0

    class _Odd:
        status = "200"

        def read(self) -> str:
            return "nope"

        def close(self) -> None:
            return None

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", lambda *_a, **_k: _Odd())
    odd = urllib_transport("http://127.0.0.1:9/v1", b"{}", {}, 1.0)
    assert odd.status == 0
    assert odd.body == b""

    class _NoRead:
        status = 200

        def close(self) -> None:
            return None

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", lambda *_a, **_k: _NoRead())
    missing = urllib_transport("http://127.0.0.1:9/v1", b"{}", {}, 1.0)
    assert missing.status == 0

    headers = Message()
    headers["Retry-After"] = "soon"
    garbage = HTTPError("http://127.0.0.1:9/v1", 429, "later", headers, io.BytesIO(b"quiet"))

    def raise_garbage(*_args: object, **_kwargs: object) -> object:
        raise garbage

    monkeypatch.setattr("a2a_gate.live.urllib_request.urlopen", raise_garbage)
    ignored = urllib_transport("http://127.0.0.1:9/v1", b"{}", {}, 1.0)
    assert ignored.retry_after_s is None


def test_retry_after_garbage_is_ignored(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            HttpResponse(429, b"slow", retry_after_s=None),
            HttpResponse(200, _body('{"proposals":[]}', ticks=1)),
        ]
    )
    delays: list[float] = []
    client = _client(transport, tmp_path / "calls.jsonl", sleeper=delays)
    client.chat(({"role": "user", "content": "one"},), case_id="hp_read")
    assert len(delays) == 1
    assert 0 < delays[0] <= 8


def _marker_case(
    case_id: str,
    record_id: str,
    message: str,
    decisions: tuple[Decision, ...] = (),
) -> EvalCase:
    return EvalCase(
        id=case_id,
        category="edge",
        title="live log",
        requester_id="requester.ana",
        requester_role="requester",
        message=message,
        record_id=record_id,
        idempotency_key=case_id,
        proposals=(),
        tokens_in=0,
        tokens_out=0,
        decisions=decisions,
        downstream_failures=0,
        kill_at="",
        use_fake_planner=False,
        probe="",
        replay_create=False,
        expect_state="completed",
        expect_applied=0,
        expect_error="",
    )


def test_action_result_uses_gate_fields_only() -> None:
    executed = action_result(
        ActionFact("issue_credit_note", "auto", "not_required", "applied", "ok")
    )
    assert executed == {"action": "issue_credit_note", "result": "executed"}
    waiting = action_result(
        ActionFact(
            "change_supplier_bank",
            "needs_approval",
            "pending",
            "not_run",
            "approval_pending",
        )
    )
    assert waiting["result"] == "input-required"
    assert "reason_code" not in waiting
    blocked = action_result(
        ActionFact("issue_credit_note", "auto", "not_required", "blocked", "kill_switch")
    )
    assert blocked["reason_code"] == "kill_switch"
    expired = action_result(
        ActionFact("issue_credit_note", "needs_approval", "expired", "not_run", "expired")
    )
    assert expired["result"] == "rejected"
    assert expired["reason_code"] == "expired"
    dead = action_result(
        ActionFact("issue_credit_note", "auto", "not_required", "dead_letter", "dead_letter")
    )
    assert dead["reason_code"] == "dead_letter"
    odd = action_result(
        ActionFact("send_customer_notice", "forbidden", "not_required", "not_run", "free text")
    )
    assert odd["reason_code"] == "unlisted"
    assert odd["action"] == "send_customer_notice"
    leaked = action_result(
        ActionFact(INJECTION_NOTE, "forbidden", "not_required", "not_run", "forbidden")
    )
    assert leaked["action"] == "redacted_name"
    assert INJECTION_NOTE not in json.dumps(leaked)


def test_live_log_records_names_and_gate_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_param = "RAWPARAM997"
    leak_mail = "leak" + "@" + "example.test"

    def plan_for(message: str) -> str:
        if message == "MIX":
            proposals = [
                {
                    "action": "read_record",
                    "record_id": "INV-1001",
                    "note": INJECTION_NOTE,
                    "extra": raw_param,
                },
                {"action": "issue_credit_note", "record_id": "INV-1001", "email": leak_mail},
                {"action": "not_a_real_action", "record_id": "INV-1001"},
                {"action": INJECTION_NOTE, "record_id": "INV-1001", "account": "100020003000"},
            ]
        elif message == "BANK":
            proposals = [
                {
                    "action": "change_supplier_bank",
                    "record_id": "SUP-2001",
                    "extra": raw_param,
                }
            ]
        else:
            proposals = [
                {"action": "issue_credit_note", "record_id": "INV-1002", "extra": raw_param}
            ]
        return json.dumps({"proposals": proposals})

    auto_attempts = {"n": 0}

    def transport(url: str, body: bytes, headers: dict[str, str], timeout_s: float) -> HttpResponse:
        del url, headers, timeout_s
        payload = json.loads(body.decode("utf-8"))
        messages = payload["messages"]
        user = json.loads(messages[1]["content"])
        message = str(user["request"])
        content = plan_for(message)
        if message == "AUTO":
            auto_attempts["n"] += 1
            if auto_attempts["n"] == 1:
                return HttpResponse(500, b"later")
        return HttpResponse(200, _body(content, ticks=10, prompt=8, completion=4, cached=0))

    bank = _marker_case(
        "log_bank",
        "SUP-2001",
        "BANK",
        (
            Decision(
                op="reject",
                actor_id="approver.finance",
                actor_role="finance_approver",
                action="change_supplier_bank",
                record_id="SUP-2001",
                seconds=0,
                expect_error="",
            ),
        ),
    )
    report = execute_live(
        evals_dir=ROOT / "evals",
        out_dir=tmp_path / "run",
        settings=_settings(max_attempts=2),
        transport=transport,
        label="unit",
        cases=(
            _marker_case("log_mix", "INV-1001", "MIX"),
            bank,
            _marker_case("log_auto", "INV-1002", "AUTO"),
        ),
        sleeper=lambda delay: None,
    )
    assert report.aborted == ""
    text = (tmp_path / "run" / "calls.jsonl").read_text(encoding="utf-8")
    lines = [json.loads(line) for line in text.splitlines()]
    assert lines
    assert all(isinstance(line, dict) for line in lines)
    assert INJECTION_NOTE not in text
    assert raw_param not in text
    assert leak_mail not in text
    assert _key() not in text
    assert "100020003000" not in text
    assert "Bearer" not in text
    summary_text = (tmp_path / "run" / "summary.json").read_text(encoding="utf-8")
    assert INJECTION_NOTE not in summary_text
    failed = [line for line in lines if line["http_status"] == 500]
    assert failed
    assert failed[0]["proposed_action_names"] == []
    assert failed[0]["action_results"] == []
    by_case = {line["case"]: line for line in lines if line["http_status"] == 200}
    mix = by_case["log_mix"]
    assert mix["proposed_action_names"] == [
        "read_record",
        "issue_credit_note",
        "not_a_real_action",
        "redacted_name",
    ]
    mix_results = {item["action"]: item for item in mix["action_results"]}
    assert mix_results["read_record"]["result"] == "accepted"
    assert mix_results["issue_credit_note"]["result"] == "input-required"
    assert "reason_code" not in mix_results["issue_credit_note"]
    assert mix_results["not_a_real_action"]["result"] == "rejected"
    assert mix_results["not_a_real_action"]["reason_code"] == "forbidden"
    assert mix_results["redacted_name"]["result"] == "rejected"
    bank_line = by_case["log_bank"]
    assert bank_line["action_results"][0]["result"] == "rejected"
    assert bank_line["action_results"][0]["reason_code"] == "rejected"
    auto = by_case["log_auto"]
    assert auto["action_results"][0]["result"] == "executed"
    assert "reason_code" not in auto["action_results"][0]
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert summary["proposals_by_action"] == {
        "change_supplier_bank": 1,
        "issue_credit_note": 2,
        "not_a_real_action": 1,
        "read_record": 1,
        "redacted_name": 1,
    }
    assert summary["proposals_rejected"] == 3
    assert summary["proposals_approval_requested"] == 2
    assert summary["proposals_unknown_or_out_of_policy"] == 2
    assert "proposals_by_action: change_supplier_bank=1" in report.text
    assert "proposals_rejected: 3" in report.text
    monkeypatch.delenv("LIVE_ENABLED", raising=False)
    assert main(["live"]) == 2
