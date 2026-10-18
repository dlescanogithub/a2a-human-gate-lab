import argparse
from pathlib import Path

from a2a_gate.errors import ConfigError
from a2a_gate.evalkit.live_run import live_cli
from a2a_gate.evalkit.suite import run_regression, run_suite, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2a-gate-eval")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="replay cassettes and fail on a broken invariant")
    run.add_argument("--evals", type=Path, default=None)
    run.add_argument("--report", type=Path, default=None)
    regression = sub.add_parser("regression", help="prove the gate can go red")
    regression.add_argument("--evals", type=Path, default=None)
    live = sub.add_parser("live", help="opt-in xAI planner. Refuses unless LIVE_ENABLED=1")
    live.add_argument("--evals", type=Path, default=None)
    live.add_argument("--out", type=Path, default=None)
    live.add_argument("--label", default="live")
    args = parser.parse_args(argv)
    evals_dir = args.evals or _default_evals()
    if args.command == "live":
        try:
            return live_cli(evals_dir, args.out, args.label)
        except ConfigError as exc:
            print(f"live: {exc.reason_code}. No request was sent.")
            return 2
    if args.command == "regression":
        report = run_regression(evals_dir)
        print(report.text)
        return 0 if report.ok else 1
    report = run_suite(evals_dir)
    print(report.text)
    write_report(report, args.report or evals_dir / "results" / "latest.json")
    return 0 if report.ok else 1


def _default_evals() -> Path:
    return Path(__file__).resolve().parents[3] / "evals"


if __name__ == "__main__":
    raise SystemExit(main())
