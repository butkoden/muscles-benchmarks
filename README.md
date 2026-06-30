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

## Current Stage

The benchmark is intentionally lightweight. It does not use special benchmark
optimizations, hidden caches or production network servers. Each row runs a
small real framework scenario through the public APIs and reports plain
avg/min/max timings.

Report sections:

- `core`: response helpers (`JsonResponse`, `HtmlResponse`, `BytesResponse`,
  `NoContentResponse`);
- `web`: ASGI and WSGI pages, API `GET`, API `POST`, and OpenAPI schema checks
  measured separately;
- `data`: no-SQL use case, no-SQL action dispatch, SQL `map_model()`, and SQL
  transaction rollback;
- `cli`: nested `muscles-cli` command arguments;
- `adapters`: MCP, JSON-RPC, SSE, and OTel adapter paths;
- `contracts`: inspect contract, correctness, architecture, and DX sanity
  checks;
- `contours`: fairness labels explaining which rows can be compared;
- `thresholds`: CI-friendly regression gate.

Contours are intentionally explicit:

```text
in-process-asgi
in-process-wsgi
in-process-api
no-sql
sql-memory
cli-in-process
adapter-in-process
stream-transport
observability
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
    asgi_public = Context(AsgiStrategy, params={"profile": "public"})
    asgi_admin = Context(AsgiStrategy, params={"profile": "admin"})

    cli = Context(CliStrategy)

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
PYTHONPATH=../muscles/src:../muscles-asgi/src:../muscles-wsgi/src:../muscles-cli/src:../muscles-sql/src:../muscles-sse/src:../muscles-jsonrpc/src:../muscles-mcp/src:../muscles-otel/src:src python -m muscles_benchmarks.runner --iterations 1000
```

### Run tests

```bash
PYTHONPATH=../muscles/src:../muscles-asgi/src:../muscles-wsgi/src:../muscles-cli/src:../muscles-sql/src:../muscles-sse/src:../muscles-jsonrpc/src:../muscles-mcp/src:../muscles-otel/src:src python -m pytest -q
```
