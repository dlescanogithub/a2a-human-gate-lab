.PHONY: setup demo test eval eval-regression lint format check-secretscan

PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e ".[dev]"
	.venv/bin/pre-commit install

demo:
	$(PYTHON) -m a2a_gate demo

test:
	$(PYTHON) -m pytest --cov-fail-under=80

eval:
	$(PYTHON) -m a2a_gate.evalkit run

# Expected to exit non-zero. That is the gate going red on purpose.
eval-regression:
	$(PYTHON) -m a2a_gate.evalkit regression

lint: check-secretscan
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy
	$(PYTHON) -m a2a_gate.secretscan

check-secretscan:
	$(PYTHON) -c 'import hashlib,re; from pathlib import Path; digest=hashlib.sha256(Path("src/a2a_gate/secretscan.py").read_bytes()).hexdigest(); text=Path("docs/PROVENANCE.md").read_text(encoding="utf-8"); found=re.search(r"(?m)^sha256: ([0-9a-f]{64})$$", text); assert found and found.group(1)==digest, digest; print("secretscan sha256 ok")'

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .
