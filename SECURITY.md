# Security

This is a local lab with a human gate. It is not a hosted service.

## Secrets

- No API keys, tokens, or private keys belong in the repo.
- `.env.example` lists variables and leaves `API_TOKEN`, `ADMIN_TOKEN`, and `LLM_API_KEY` empty. Live mode is off unless `LIVE_MODE=1`. CI does not set it.
- The process reads configuration from the environment. The fake planner is the default and needs no key.
- The demo generates in-process tokens, prints that they are NOT REAL, and does not write them to the evidence file.
- CI runs `python -m a2a_gate.secretscan` and gitleaks 8.30.1. The gitleaks tarball is checked against a pinned SHA-256 before it runs.
- `src/a2a_gate/secretscan.py` is the byte-identical copy from the public repo named in `docs/PROVENANCE.md`. `make check-secretscan` recomputes that hash. Finding ids name key shapes. They are not a claim of affiliation with any company.

## What the planner is not allowed to do

- It has no approve tool. Approval is an HTTP call from a different actor.
- It does not choose the idempotency key.
- It does not set the credit-note amount.
- Claims that the action is already approved are ignored.
- `issue_credit_note` above the auto band and `change_supplier_bank` do not run until a person decides.
- `send_customer_notice` and `procurement_exception` are forbidden.
- INFO logs and the evidence file do not include the customer note, the email, or the account number.

## The API

`python -m a2a_gate serve` refuses to start unless `API_TOKEN` and `ADMIN_TOKEN` are set. Every route except `GET /health` and `GET /.well-known/agent-card.json` requires `Authorization: Bearer`. The kill switch also requires `X-Admin-Token`. Both comparisons hash the values before `hmac.compare_digest`. The default bind is `127.0.0.1`. Do not put it on a public interface. A real identity provider is design-only. This bearer is the minimum, not that login.

The evidence file is the other boundary. Write access to it is the ability to forge history if the attacker also recomputes hashes. Protect the file the way you would protect a log you claim to trust. `verify-evidence` detects a naive edit. It does not detect a full rewrite.

## CI

GitHub Actions workflow `.github/workflows/ci.yml` runs one job, `ci`:

| Step | What it runs |
|---|---|
| lint | `ruff check`, `ruff format --check` |
| typecheck | `mypy` (strict on `a2a_gate`) |
| test | `pytest` with coverage, floor 80%, summary via `scripts/write_coverage_summary.py` |
| eval | cassette suite must pass; forced regression must exit non-zero |
| secrets | the Python scanner and gitleaks 8.30.1, checksum pinned |

This repository does not enable branch protection. That is a setting on the GitHub repository. Before `main` accepts merges, require the `ci` job and a review from someone who did not write the change.

## Dependency pinning

Runtime dependencies: none. Dev tools are pinned in `pyproject.toml` (`ruff==0.17.1`, `mypy==2.4.0`, `pytest==9.1.1`, `pytest-cov==7.1.0`, `coverage==7.16.2`, `pre-commit==4.7.0`). The Docker image is `python:3.12-slim`. Actions are pinned to major tags (`actions/checkout@v4`, `actions/setup-python@v5`). Pinning those tags to commit SHAs is a reasonable next step, not done here.

## Reporting

This is a portfolio repository, not a production service. There is no bounty. Use GitHub private vulnerability reporting if the repository offers it. The useful review question is whether a new effect was added without a gate.
