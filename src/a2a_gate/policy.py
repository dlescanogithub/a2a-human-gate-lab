"""Risk policy loaded from the lab YAML file.

The file is the contract. Unknown actions are forbidden. The model does not
get a vote on the disposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from a2a_gate.errors import ValidationError

Disposition = Literal["auto", "needs_approval", "forbidden"]

_DISPOSITIONS: frozenset[str] = frozenset({"auto", "needs_approval", "forbidden"})


@dataclass(frozen=True)
class ActionRule:
    action: str
    disposition: Disposition
    auto_below_cents: int | None
    forbidden_above_cents: int | None
    forbid_non_positive: bool


@dataclass(frozen=True)
class Policy:
    approval_ttl_seconds: int
    approver_roles: frozenset[str]
    rules: tuple[ActionRule, ...]

    def rule_for(self, action: str) -> ActionRule | None:
        for rule in self.rules:
            if rule.action == action:
                return rule
        return None

    def classify(self, action: str, amount_cents: int) -> Disposition:
        rule = self.rule_for(action)
        if rule is None or rule.disposition == "forbidden":
            return "forbidden"
        if rule.disposition == "auto":
            return "auto"
        if rule.forbid_non_positive and amount_cents <= 0:
            return "forbidden"
        if rule.forbidden_above_cents is not None and amount_cents > rule.forbidden_above_cents:
            return "forbidden"
        if rule.auto_below_cents is not None and amount_cents < rule.auto_below_cents:
            return "auto"
        return "needs_approval"


def default_policy_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "nube_austral.yaml"


def load_default_policy() -> Policy:
    return load_policy_text(default_policy_path().read_text(encoding="utf-8"))


def load_policy_text(text: str) -> Policy:
    ttl: int | None = None
    roles: list[str] = []
    specs: dict[str, dict[str, str]] = {}
    in_actions = False
    in_roles = False
    current: str | None = None

    for raw in text.splitlines():
        if "#" in raw:
            raw = raw.split("#", 1)[0]
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0 and line.endswith(":") and ": " not in line:
            key = line[:-1].strip()
            in_actions = key == "actions"
            in_roles = key == "approver_roles"
            current = None
            continue
        if indent == 0 and ": " in line:
            key, value = _split_pair(line)
            if key != "approval_ttl_seconds":
                raise ValidationError("policy_yaml")
            ttl = _required_int(value, "approval_ttl_seconds")
            in_actions = False
            in_roles = False
            current = None
            continue
        if in_roles and line.startswith("- "):
            role = line[2:].strip()
            if role == "":
                raise ValidationError("policy_yaml")
            roles.append(role)
            continue
        if in_actions and indent == 2 and line.endswith(":") and ": " not in line:
            current = line[:-1].strip()
            if current == "":
                raise ValidationError("policy_yaml")
            specs[current] = {}
            continue
        if in_actions and current is not None and indent == 4 and ": " in line:
            key, value = _split_pair(line)
            specs[current][key] = value
            continue
        raise ValidationError("policy_yaml")

    if ttl is None or ttl <= 0 or not roles or not specs:
        raise ValidationError("policy_yaml")
    rules = tuple(_rule(name, spec) for name, spec in specs.items())
    return Policy(
        approval_ttl_seconds=ttl,
        approver_roles=frozenset(roles),
        rules=rules,
    )


def _rule(name: str, spec: dict[str, str]) -> ActionRule:
    raw = spec.get("disposition", "")
    if raw not in _DISPOSITIONS:
        raise ValidationError("policy_yaml")
    disposition: Disposition = "auto"
    if raw == "needs_approval":
        disposition = "needs_approval"
    elif raw == "forbidden":
        disposition = "forbidden"
    return ActionRule(
        action=name,
        disposition=disposition,
        auto_below_cents=_optional_int(spec.get("auto_below_cents")),
        forbidden_above_cents=_optional_int(spec.get("forbidden_above_cents")),
        forbid_non_positive=spec.get("forbid_non_positive", "false") == "true",
    )


def _split_pair(line: str) -> tuple[str, str]:
    key, value = line.split(": ", 1)
    key = key.strip()
    value = value.strip()
    if key == "" or value == "":
        raise ValidationError("policy_yaml")
    return key, value


def _required_int(value: str, field: str) -> int:
    if not value.isdigit():
        raise ValidationError(field)
    return int(value)


def _optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    if not value.isdigit():
        raise ValidationError("policy_yaml")
    return int(value)
