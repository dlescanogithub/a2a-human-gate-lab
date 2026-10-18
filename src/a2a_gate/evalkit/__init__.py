"""Eval gate. Deterministic checks always block. The checklist is code, not a model."""

from a2a_gate.evalkit.suite import run_regression, run_suite

__all__ = ["run_regression", "run_suite"]
