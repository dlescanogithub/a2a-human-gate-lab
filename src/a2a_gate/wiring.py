"""Build the runtime the server and the demo actually run.

The gate is on. There is no environment flag that turns it off.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path

from a2a_gate.clock import Clock
from a2a_gate.config import Config
from a2a_gate.downstream import FakeDownstream
from a2a_gate.evidence import EvidenceLog
from a2a_gate.planner import FakePlanner
from a2a_gate.policy import load_default_policy
from a2a_gate.runtime import Runtime


def build_runtime(
    config: Config,
    *,
    clock: Clock,
    evidence_path: Path | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> Runtime:
    path = config.evidence_path if evidence_path is None else evidence_path
    return Runtime(
        policy=load_default_policy(),
        evidence=EvidenceLog(path, clock),
        downstream=FakeDownstream(),
        clock=clock,
        planner=FakePlanner(),
        admin_token=config.admin_token,
        enforce_gate=True,
        max_attempts=config.max_attempts,
        rng=random.Random(config.seed),
        sleeper=sleeper if sleeper is not None else _no_sleep,
    )


def _no_sleep(delay: float) -> None:
    del delay
