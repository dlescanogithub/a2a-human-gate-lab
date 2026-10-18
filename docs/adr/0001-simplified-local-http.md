# 0001 Simplified local HTTP

## Status

Accepted. 2026-10-18.

## Context

The public A2A notes describe an agent card, tasks, and several bindings (JSON-RPC, gRPC, HTTP+JSON), plus streaming and push. Re-read on 2026-10-18 from the links in `docs/architecture.md`. Building a conforming stack is not the point of the lab.

## Decision

Serve a small stdlib HTTP API on `127.0.0.1`. Publish a card at `/.well-known/agent-card.json`. Use the state names `submitted`, `working`, `input-required`, `completed`, `failed`, `canceled`, and `rejected`. Label the binding `LAB-HTTP`. Map human approval to `input-required` / `approval-pending`. Do not implement `auth-required`, streaming, push, or signed cards.

## Consequences

A reader can see the task lifecycle without mistaking the process for a certified A2A endpoint. A later conformance pass would be a new project.
