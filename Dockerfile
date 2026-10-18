# Local demo image. The default command uses the fake planner and no secrets.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 appuser

USER appuser

ENV LLM_PROVIDER=fake \
    LIVE_MODE=0 \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "a2a_gate", "demo", "--evidence", "/tmp/demo-evidence.jsonl"]
