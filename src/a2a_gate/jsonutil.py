"""Small JSON helpers.

json.loads is typed as Any. These wrappers narrow the value before the rest
of the code sees it, which is what lets the package type-check in strict mode.

Adapted from agent-runtime-evals (see docs/PROVENANCE.md). The import path
and the error type are local. The checks are the same idea.
"""

from __future__ import annotations

import json
from typing import cast

from a2a_gate.errors import ValidationError


def loads(text: str) -> object:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("invalid_json") from exc
    return cast(object, parsed)


def dumps(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError("expected_object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValidationError("expected_object")
        result[key] = item
    return result


def as_str(value: object, field: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValidationError(f"{field}_invalid")
    return value


def as_optional_str(value: object, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field}_invalid")
    return value


def as_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field}_invalid")
    return value


def as_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field}_invalid")
    return value


def as_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{field}_invalid")
    return cast(list[object], value)
