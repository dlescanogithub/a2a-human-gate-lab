"""Fake downstream ledger with bounded retries and a dead-letter outcome.

The sleeper is injected. Tests pass a no-op. The delay itself comes from the
vendored backoff helper, which caps the wait.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from a2a_gate.errors import TransientError
from a2a_gate.providers.backoff import retry_delay_s

EffectResult = Literal["applied", "dead_letter"]


@dataclass(frozen=True)
class AttemptResult:
    status: EffectResult
    attempts: int


class FakeDownstream:
    """In-memory ledger. ``fail_remaining`` raises before a successful apply."""

    def __init__(self, fail_remaining: int = 0) -> None:
        if fail_remaining < 0:
            raise ValueError("fail_remaining")
        self.fail_remaining = fail_remaining
        self.applied: list[str] = []

    def apply(self, effect_key: str) -> None:
        if self.fail_remaining > 0:
            self.fail_remaining -= 1
            raise TransientError("downstream_unavailable")
        if effect_key not in self.applied:
            self.applied.append(effect_key)


def call_with_retries(
    downstream: FakeDownstream,
    effect_key: str,
    *,
    max_attempts: int,
    rng: random.Random,
    sleeper: Callable[[float], None],
) -> AttemptResult:
    if max_attempts < 1:
        raise ValueError("max_attempts")
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            downstream.apply(effect_key)
        except TransientError:
            if attempts >= max_attempts:
                break
            delay = retry_delay_s(attempts, None, rng)
            sleeper(delay)
            continue
        return AttemptResult("applied", attempts)
    return AttemptResult("dead_letter", attempts)
