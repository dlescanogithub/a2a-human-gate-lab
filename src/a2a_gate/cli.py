"""Command line. ``python -m a2a_gate`` works when make is not installed."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from a2a_gate.card import build_card
from a2a_gate.clock import WallClock
from a2a_gate.config import Config
from a2a_gate.demo import run_demo
from a2a_gate.evidence import verify
from a2a_gate.http_api import serve
from a2a_gate.logging_setup import configure
from a2a_gate.wiring import build_runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2a-gate")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run the local walkthrough")
    demo.add_argument("--evidence", type=Path, default=Path("var/demo-evidence.jsonl"))
    sub.add_parser("serve", help="serve the local HTTP API")
    verify_cmd = sub.add_parser("verify-evidence", help="check the hash chain")
    verify_cmd.add_argument("path", type=Path)
    sub.add_parser("card", help="print the agent card JSON")
    args = parser.parse_args(argv)
    if args.command == "demo":
        configure("INFO")
        code, lines = run_demo(args.evidence)
        for line in lines:
            print(line)
        return code
    if args.command == "card":
        print(json.dumps(build_card(Config.from_env().public_base_url), indent=2, sort_keys=True))
        return 0
    if args.command == "verify-evidence":
        ok, detail = verify(args.path)
        print(detail)
        return 0 if ok else 1
    if args.command == "serve":
        config = Config.from_env()
        try:
            config.require_server_tokens()
        except ValueError:
            print("API_TOKEN and ADMIN_TOKEN are required", file=sys.stderr)
            return 2
        configure(config.log_level)
        runtime = build_runtime(config, clock=WallClock(), sleeper=time.sleep)
        serve(config, runtime)
        return 0
    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
