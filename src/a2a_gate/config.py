"""Environment-only configuration. Nothing here has a default secret."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw == "":
        return default
    if not raw.isdigit():
        raise ValueError(name)
    return int(raw)


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    public_base_url: str
    api_token: str
    admin_token: str
    evidence_path: Path
    log_level: str
    llm_provider: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    live_mode: bool
    max_attempts: int
    seed: int

    @classmethod
    def from_env(cls) -> Config:
        host = os.environ.get("A2A_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = _int("A2A_PORT", 8765)
        base = os.environ.get("PUBLIC_BASE_URL", f"http://{host}:{port}").strip()
        return cls(
            host=host,
            port=port,
            public_base_url=base or f"http://{host}:{port}",
            api_token=os.environ.get("API_TOKEN", ""),
            admin_token=os.environ.get("ADMIN_TOKEN", ""),
            evidence_path=Path(os.environ.get("EVIDENCE_PATH", "var/evidence.jsonl")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").strip() or "INFO",
            llm_provider=os.environ.get("LLM_PROVIDER", "fake").strip() or "fake",
            llm_api_key=os.environ.get("LLM_API_KEY", ""),
            llm_base_url=os.environ.get("LLM_BASE_URL", ""),
            llm_model=os.environ.get("LLM_MODEL", ""),
            live_mode=os.environ.get("LIVE_MODE", "0").strip() == "1",
            max_attempts=_int("MAX_DOWNSTREAM_ATTEMPTS", 3),
            seed=_int("SEED", 42),
        )

    def require_server_tokens(self) -> None:
        if self.api_token == "" or self.admin_token == "":
            raise ValueError("server_tokens")
