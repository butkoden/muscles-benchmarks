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

### Run benchmark

```bash
muscles-bench --iterations 1000 --json
```

### Run tests

```bash
PYTHONPATH=src python -m pytest -q
```
