"""Small HTTP surface. Not the A2A JSON-RPC binding and not a public host.

Protected routes need ``Authorization: Bearer``. The kill switch also needs
``X-Admin-Token``. Neither value is written to the log.
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from a2a_gate.card import build_card
from a2a_gate.config import Config
from a2a_gate.errors import AuthError, GateLabError, ValidationError
from a2a_gate.evidence import verify
from a2a_gate.jsonutil import as_dict, as_str, loads
from a2a_gate.logging_setup import log
from a2a_gate.runtime import Runtime
from a2a_gate.tokens import tokens_equal
from a2a_gate.types import Actor

MAX_BODY = 1_000_000
LOGGER = logging.getLogger("a2a_gate.http")


def dispatch(
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes,
    runtime: Runtime,
    api_token: str,
    base_url: str,
) -> tuple[int, dict[str, object]]:
    route = urlsplit(path).path
    if method == "GET" and route == "/health":
        return 200, {"status": "ok"}
    if method == "GET" and route == "/.well-known/agent-card.json":
        return 200, build_card(base_url)
    if not _authorized(headers, api_token):
        return 401, {"error": "unauthorized"}
    try:
        return _route(method, route, headers, body, runtime)
    except AuthError as exc:
        return 403, {"error": exc.reason_code}
    except ValidationError as exc:
        status = 404 if exc.reason_code == "unknown_task" else 400
        return status, {"error": exc.reason_code}
    except GateLabError as exc:
        return 400, {"error": exc.reason_code}


def _route(
    method: str,
    route: str,
    headers: dict[str, str],
    body: bytes,
    runtime: Runtime,
) -> tuple[int, dict[str, object]]:
    if method == "POST" and route == "/v1/tasks":
        payload = _object(body)
        task = runtime.create_task(
            Actor(as_str(payload.get("requester_id"), "requester_id"), _role(payload)),
            as_str(payload.get("message"), "message"),
            as_str(payload.get("record_id"), "record_id"),
            as_str(payload.get("idempotency_key"), "idempotency_key"),
        )
        return 200, runtime.snapshot(task.id)
    if method == "GET" and route.startswith("/v1/tasks/"):
        return 200, runtime.snapshot(_task_id(route))
    if method == "POST" and route.endswith(":cancel"):
        payload = _object(body)
        task_id = _task_id(route[: -len(":cancel")])
        actor = Actor(as_str(payload.get("actor_id"), "actor_id"), _role(payload))
        task = runtime.cancel(task_id, actor)
        return 200, runtime.snapshot(task.id)
    if method == "POST" and route.endswith(":approve"):
        return _decision(runtime, route, ":approve", body, reject=False)
    if method == "POST" and route.endswith(":reject"):
        return _decision(runtime, route, ":reject", body, reject=True)
    if method == "POST" and route == "/v1/admin/kill-switch":
        payload = _object(body)
        runtime.kill(
            _header(headers, "x-admin-token"),
            Actor(as_str(payload.get("actor_id"), "actor_id"), _role(payload)),
        )
        return 200, {"killed": True}
    if method == "GET" and route == "/v1/evidence/verify":
        ok, detail = verify(runtime.evidence.path)
        return (200 if ok else 409), {"ok": ok, "detail": detail}
    return 404, {"error": "not_found"}


def _decision(
    runtime: Runtime,
    route: str,
    suffix: str,
    body: bytes,
    *,
    reject: bool,
) -> tuple[int, dict[str, object]]:
    payload = _object(body)
    task_id = _task_id(route[: -len(suffix)])
    actor = Actor(as_str(payload.get("actor_id"), "actor_id"), _role(payload))
    action = as_str(payload.get("action"), "action")
    record_id = as_str(payload.get("record_id"), "record_id")
    if reject:
        task = runtime.reject(task_id, actor, action, record_id)
    else:
        task = runtime.approve(task_id, actor, action, record_id)
    return 200, runtime.snapshot(task.id)


def _task_id(route: str) -> str:
    prefix = "/v1/tasks/"
    if not route.startswith(prefix):
        raise ValidationError("unknown_task")
    task_id = route[len(prefix) :]
    if task_id == "" or "/" in task_id:
        raise ValidationError("unknown_task")
    return task_id


def _object(body: bytes) -> dict[str, object]:
    if not body:
        raise ValidationError("invalid_json")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("invalid_json") from exc
    return as_dict(loads(text))


def _role(payload: dict[str, object]) -> str:
    role = payload.get("requester_role", payload.get("actor_role"))
    return as_str(role, "role")


def _authorized(headers: dict[str, str], api_token: str) -> bool:
    value = _header(headers, "authorization")
    prefix = "Bearer "
    if not value.startswith(prefix):
        return False
    return tokens_equal(value[len(prefix) :], api_token)


def _header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return ""


def make_server(config: Config, runtime: Runtime) -> ThreadingHTTPServer:
    card_url = config.public_base_url
    token = config.api_token

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            self._handle()

        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > MAX_BODY:
                self._send(413, {"error": "body_too_large"})
                return
            raw = self.rfile.read(length) if length else b""
            headers = {key: value for key, value in self.headers.items()}
            status, payload = dispatch(
                self.command,
                self.path,
                headers,
                raw,
                runtime,
                token,
                card_url,
            )
            self._send(status, payload)

        def _send(self, status: int, payload: dict[str, object]) -> None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt: str, *args: object) -> None:
            del fmt, args
            log(
                LOGGER,
                logging.INFO,
                "http_request",
                method=self.command,
                path=urlsplit(self.path).path,
            )

    return ThreadingHTTPServer((config.host, config.port), Handler)


def serve(config: Config, runtime: Runtime) -> None:
    server = make_server(config, runtime)
    try:
        server.serve_forever()
    finally:
        server.server_close()
