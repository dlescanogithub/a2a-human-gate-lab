# Provenance

Nothing in this repository is copied from an employer or from a client engagement.

`secretscan.py`, `logging_setup.py`, `trace.py`, and `providers/backoff.py` are copied from the public repository [agent-runtime-evals](https://github.com/dlescanogithub/agent-runtime-evals) at commit `e9c96a3080468a420f2f8809e5b108ea743a7637` (2026-10-18). Those four files are byte-identical. The cassette idea, the JSON helpers, and the "invariants rather than transcripts" eval shape are adapted from that repo and are not byte-identical: imports point at `a2a_gate`, and the plan is a list of proposed actions instead of a refund tool transcript.

No file was copied from the archived public lab argentine-a2a. Only the idea of an agent card plus a task lifecycle was reused, and it was rewritten.

## Secret scanner

`src/a2a_gate/secretscan.py` is the shared scanner. Keep that file byte-for-byte identical, including this hash. The finding ids name key shapes. They are not a claim of affiliation with any company.

sha256: a3b48e9b7a413d57bbb6e06ef1e3c3194a4100195a61542ad712a87898851709

`make check-secretscan` recomputes the hash. A change to the scanner updates the hash in the same commit.

## What was written for this lab

The Nube Austral policy, the hash-chained evidence log, the human approval gate, the kill switch, the simplified task HTTP API, and the 37 scripted cases.
