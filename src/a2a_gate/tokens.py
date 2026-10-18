"""Compare credentials without putting them in logs."""

from __future__ import annotations

import hashlib
import hmac


def tokens_equal(provided: str, expected: str) -> bool:
    """True when both sides hash equal. An empty expected token never matches."""

    if expected == "" or provided == "":
        return False
    left = hashlib.sha256(provided.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)
