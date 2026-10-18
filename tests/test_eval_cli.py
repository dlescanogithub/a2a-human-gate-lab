import hashlib
from pathlib import Path

import pytest

from a2a_gate import cli
from a2a_gate.config import Config
from a2a_gate.demo import run_demo
from a2a_gate.evalkit.cases import load_cases
from a2a_gate.evalkit.checks import SECRET_PROBE
from a2a_gate.evalkit.suite import run_regression, run_suite
from a2a_gate.secretscan import scan_text

ROOT = Path(__file__).resolve().parents[1]


def test_suite_passes_and_regression_fails() -> None:
    cases = load_cases(ROOT / "evals" / "cases.json")
    assert len(cases) >= 30
    categories = {case.category for case in cases}
    assert categories == {"happy", "edge", "adversarial"}
    report = run_suite(ROOT / "evals")
    assert report.ok, report.text
    assert report.passed == len(cases)
    regression = run_regression(ROOT / "evals")
    assert not regression.ok
    assert "risky effect without approval" in regression.text


def test_demo_and_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    code, lines = run_demo(tmp_path / "demo.jsonl")
    assert code == 0
    text = "\n".join(lines)
    assert "fake provider" in text
    assert "NOT REAL" in text
    assert "self-approval: denied" in text
    assert "kill switch: halted" in text
    assert "applied effects: 1" in text
    assert "evidence: valid" in text
    assert SECRET_PROBE not in text
    assert "@" not in text
    cli_code = cli.main(["demo", "--evidence", str(tmp_path / "cli.jsonl")])
    assert cli_code == 0
    card_code = cli.main(["card"])
    assert card_code == 0
    verify_code = cli.main(["verify-evidence", str(tmp_path / "demo.jsonl")])
    assert verify_code == 0
    missing = cli.main(["verify-evidence", str(tmp_path / "missing.jsonl")])
    assert missing == 1
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert cli.main(["serve"]) == 2
    captured = capsys.readouterr()
    assert "Nube Austral" in captured.out
    assert "lab-admin" not in captured.out
    assert "sk-" not in captured.out


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("A2A_PORT", "9000")
    monkeypatch.setenv("API_TOKEN", "lab-api")
    monkeypatch.setenv("ADMIN_TOKEN", "lab-admin")
    monkeypatch.setenv("LIVE_MODE", "0")
    config = Config.from_env()
    assert config.port == 9000
    assert not config.live_mode
    config.require_server_tokens()
    blocked = Config(
        host="127.0.0.1",
        port=1,
        public_base_url="http://127.0.0.1:1",
        api_token="",
        admin_token="",
        evidence_path=Path("var/x.jsonl"),
        log_level="INFO",
        llm_provider="fake",
        llm_api_key="",
        llm_base_url="",
        llm_model="",
        live_mode=False,
        max_attempts=3,
        seed=1,
    )
    with pytest.raises(ValueError):
        blocked.require_server_tokens()


def test_secretscan_and_hygiene() -> None:
    assert scan_text("hello token") == []
    assert "github_token" in scan_text("ghp_" + ("a" * 20))
    banned = ("En" + "dava", "Rel" + "ias", "Fan " + "Universe")
    home_path = "/" + "home" + "/"
    secret_dir = "secrets" + "/"
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(
            part in {".git", ".venv", "venv", "__pycache__"} or part.endswith(".egg-info")
            for part in path.parts
        ):
            continue
        if path.suffix in {".png", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for word in banned:
            if word in text:
                offenders.append(f"{path}:{word}")
        if home_path in text or secret_dir in text:
            offenders.append(f"{path}:path")
    assert offenders == []
    digest = hashlib.sha256((ROOT / "src/a2a_gate/secretscan.py").read_bytes()).hexdigest()
    provenance = (ROOT / "docs/PROVENANCE.md").read_text(encoding="utf-8")
    assert digest in provenance


def test_jsonutil_and_tokens() -> None:
    from a2a_gate.errors import ValidationError
    from a2a_gate.jsonutil import as_bool, as_dict, as_int, as_list, as_str, dumps, loads
    from a2a_gate.tokens import tokens_equal

    assert loads(dumps({"b": 1})) == {"b": 1}
    with pytest.raises(ValidationError):
        loads("{")
    with pytest.raises(ValidationError):
        as_dict([])
    with pytest.raises(ValidationError):
        as_str("", "field")
    with pytest.raises(ValidationError):
        as_int(True, "field")
    with pytest.raises(ValidationError):
        as_bool("true", "field")
    with pytest.raises(ValidationError):
        as_list({}, "field")
    assert tokens_equal("lab-api", "lab-api")
    assert not tokens_equal("", "lab-api")
    assert not tokens_equal("lab-api", "other")
