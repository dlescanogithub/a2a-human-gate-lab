"""Time source. Tests and evals use a fixed clock; the server uses the wall clock."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def time(self) -> int:
        """Unix seconds."""

    def advance(self, seconds: int) -> None:
        """Move a fake clock forward. The wall clock refuses this."""


class ManualClock:
    def __init__(self, start: int = 1_700_000_000) -> None:
        self._now = start

    def time(self) -> int:
        return self._now

    def advance(self, seconds: int) -> None:
        if seconds < 0:
            raise ValueError("seconds")
        self._now += seconds


class WallClock:
    def time(self) -> int:
        return int(time.time())

    def advance(self, seconds: int) -> None:
        del seconds
        raise RuntimeError("wall_clock")
