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
