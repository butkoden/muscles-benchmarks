# Muscles Benchmarks

Official benchmark and regression suite for the Muscles framework ecosystem.

This repository must measure the canonical Muscles golden path, not random local
experiments. Benchmarks must use public APIs exactly as users and AI agents are
expected to use them.

## Concept Guardrails

- Muscles is one application model with multiple ways to speak to it.
- Benchmarks must cover the same feature through ASGI, WSGI, CLI, SQL, and future
  protocol adapters where applicable.
- Do not duplicate business logic per transport.
- Do not benchmark deprecated or non-canonical usage patterns.
- Every benchmark must explain what it measures and which package owns the
  optimization if the result regresses.

## Initial Goal

Create a Booking benchmark app that uses:

- `JsonResponse` and `HtmlResponse`;
- `/docs` and `/openapi.json`;
- `muscles-cli` nested command arguments;
- `muscles-sql map_model()` with real Muscles columns;
- a repeatable command set for local and CI runs.

## Current Stage (Issues #1 and #3)

Implemented official Booking golden path benchmark and fair matrix baseline:

- shared booking use case reused across surfaces;
- real `muscles.core` response helpers:
  - `JsonResponse`
  - `HtmlResponse`
- real `/docs` and `/openapi.json` alias checks for both ASGI and WSGI routers;
- real nested CLI command arguments through `muscles-cli` group owner:
  - `--limit 3`
  - `--limit=3`
- real `muscles-sql map_model()` path with `muscles.Column(Integer/String/DateTime)`,
  autoincrement PK, insert without explicit id;
- fair matrix section:
  - direct ASGI/WSGI contour benchmark;
  - network matrix metadata with contour classification and guardrails.

## Proof-suite Stage (Issue #4)

The benchmark now also acts as an architecture and DX proof-suite. It measures
whether Muscles keeps one Booking application model across multiple protocol
projections, not only raw RPS.

Report sections:

- `booking_domain`: canonical Booking actions, schemas, rules, transports and
  shared use-case calls;
- `golden_path`: response helpers, docs/OpenAPI aliases, CLI nested args,
  SQL model mapping;
- `correctness`: action dispatch, validation errors, permission/rules and
  inspect contract checks;
- `architecture`: shared use case, duplicated business logic count, projection
  count and architecture score;
- `dx`: source/DX-oriented metrics for vibe-coding and AI-assisted changes;
- `streaming`: SSE heartbeat/user-event/backpressure checks;
- `observability`: OTel disabled/enabled lifecycle overhead;
- `transactions`: SQL commit/rollback behavior;
- `contours`: benchmark fairness contour taxonomy;
- `thresholds`: CI-friendly regression gate.

Contours are intentionally explicit:

```text
direct-no-network
in-process-adapter
network-prod
network-dev-reference
subprocess-cli
cold-start
stream-transport
observability
transaction
```

This keeps comparisons honest: rows from different contours should not be
compared as if they measured the same thing.

### Multi-context contract checks

The benchmark app model is intentionally exercised through multiple entrypoint
profiles, all backed by one action model:

```python
from muscles import ApplicationMeta, Context
from muscles.cli import CliStrategy
from muscles.asgi import AsgiStrategy
from muscles_mcp import McpStrategy


class BookingBenchApp(metaclass=ApplicationMeta):
    asgi_public = Context(AsgiStrategy, transport="asgi", params={"profile": "public"})
    asgi_admin = Context(AsgiStrategy, transport="asgi", params={"profile": "admin"})

    cli = Context(CliStrategy, transport="cli")

    mcp_public = Context(McpStrategy, transport=asgi_public, params={"mcp_profile": "public"})
    mcp_private = Context(McpStrategy, transport=asgi_admin, params={"mcp_profile": "private"})
```

`McpStrategy` contexts can bind to concrete ASGI profiles through
`transport=<entrypoint_context>`, while contract discovery and action registration
remain one for all projections.

### Run benchmark

```bash
muscles-bench --iterations 1000 --json
```

Local source checkout example:

```bash
PYTHONPATH=src python -m muscles_benchmarks.runner --iterations 10 --json
```

### Run tests

```bash
PYTHONPATH=src python -m pytest -q
```
