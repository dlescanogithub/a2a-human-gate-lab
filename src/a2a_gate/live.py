"""Optional hosted-model adapter. Off unless LIVE_MODE=1 and a key are set.

CI does not set those variables. This lab has no measured run against a
hosted model. The default opener is urllib; tests pass a fake opener.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib import request as urllib_request

from a2a_gate.config import Config
from a2a_gate.errors import ConfigError

Opener = Callable[[object, int], bytes]


def live_allowed(config: Config) -> bool:
    return bool(
        config.live_mode
        and config.llm_provider == "openai"
        and config.llm_api_key != ""
        and config.llm_base_url != ""
        and config.llm_model != ""
    )


def build_request(model: str, prompt: str) -> dict[str, object]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }


def send(config: Config, prompt: str, opener: Opener | None = None) -> str:
    if not live_allowed(config):
        raise ConfigError("live_off")
    body = json.dumps(build_request(config.llm_model, prompt)).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + config.llm_api_key,
    }
    chosen = opener if opener is not None else urllib_opener
    raw = chosen(_prepared(config.llm_base_url, body, headers), 5)
    return _content(raw)


def urllib_opener(req: object, timeout: int) -> bytes:
    if not isinstance(req, urllib_request.Request):
        raise ConfigError("live_bad_request")
    response = urllib_request.urlopen(req, timeout=timeout)
    try:
        reader = getattr(response, "read", None)
        if not callable(reader):
            raise ConfigError("live_bad_response")
        data: object = reader()
    finally:
        closer = getattr(response, "close", None)
        if callable(closer):
            closer()
    if not isinstance(data, bytes):
        raise ConfigError("live_bad_response")
    return data


def _prepared(url: str, body: bytes, headers: dict[str, str]) -> urllib_request.Request:
    return urllib_request.Request(url, data=body, headers=headers, method="POST")


def _content(raw: bytes) -> str:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError("live_bad_response") from exc
    if not isinstance(parsed, dict):
        raise ConfigError("live_bad_response")
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ConfigError("live_bad_response")
    first = choices[0]
    if not isinstance(first, dict):
        raise ConfigError("live_bad_response")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ConfigError("live_bad_response")
    content = message.get("content")
    if not isinstance(content, str):
        raise ConfigError("live_bad_response")
    return content
