from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from statistics import mean
from time import perf_counter

from .golden_path import (
    benchmark_architecture_metrics,
    benchmark_booking_domain_alignment,
    benchmark_cli_nested_limit,
    benchmark_core_responses,
    benchmark_correctness_checks,
    benchmark_direct_matrix,
    benchmark_dx_metrics,
    benchmark_extension_ai_contract,
    benchmark_extension_documents_pipeline,
    benchmark_otel_overhead,
    benchmark_openapi_docs_aliases,
    benchmark_sql_transaction,
    benchmark_sql_map_model,
    benchmark_sse_stream,
    build_contour_matrix,
    evaluate_thresholds,
)


def _measure(callback, iterations: int) -> dict:
    samples = []
    last_result = None
    for _ in range(iterations):
        started = perf_counter()
        last_result = callback()
        samples.append((perf_counter() - started) * 1000.0)
    return {
        "avg_ms": round(mean(samples), 6),
        "min_ms": round(min(samples), 6),
        "max_ms": round(max(samples), 6),
        "result": last_result,
    }


def _pkg_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def build_network_matrix() -> dict:
    # Stage #3 baseline: declare fair matrix and classify server contours.
    return {
        "fairness_rule": "Do not compare production ASGI server with development-only WSGI server without explicit contour label.",
        "servers": [
            {"runtime": "asgi", "server": "uvicorn", "contour": "network-prod"},
            {"runtime": "asgi", "server": "hypercorn", "contour": "network-prod"},
            {"runtime": "wsgi", "server": "gunicorn", "contour": "network-prod"},
            {"runtime": "wsgi", "server": "waitress", "contour": "network-prod"},
            {"runtime": "wsgi", "server": "wsgiref", "contour": "network-dev-reference"},
        ],
    }


def run_benchmarks(iterations: int = 100) -> dict:
    report = {
        "iterations": iterations,
        "metadata": {
            "python": platform.python_version(),
            "packages": {
                "muscles": _pkg_version("muscles"),
                "muscles-cli": _pkg_version("muscles-cli"),
                "muscles-sql": _pkg_version("muscles-sql"),
                "muscles-asgi": _pkg_version("muscles-asgi"),
                "muscles-wsgi": _pkg_version("muscles-wsgi"),
                "muscles-sse": _pkg_version("muscles-sse"),
                "muscles-otel": _pkg_version("muscles-otel"),
                "muscles-ai": _pkg_version("muscles-ai"),
                "muscles-documents": _pkg_version("muscles-documents"),
            },
        },
        "booking_domain": _measure(benchmark_booking_domain_alignment, iterations),
        "golden_path": {
            "responses": _measure(benchmark_core_responses, iterations),
            "openapi_docs_aliases": _measure(benchmark_openapi_docs_aliases, iterations),
            "cli_nested_limit": _measure(benchmark_cli_nested_limit, iterations),
            "sql_map_model": _measure(benchmark_sql_map_model, iterations),
        },
        "correctness": {
            "action_dispatch": _measure(benchmark_correctness_checks, iterations),
        },
        "architecture": {
            "metrics": _measure(benchmark_architecture_metrics, iterations),
        },
        "dx": {
            "metrics": _measure(benchmark_dx_metrics, iterations),
        },
        "streaming": {
            "sse": _measure(benchmark_sse_stream, iterations),
        },
        "observability": {
            "otel": _measure(benchmark_otel_overhead, iterations),
        },
        "transactions": {
            "sql": _measure(benchmark_sql_transaction, iterations),
        },
        "extensions": {
            "ai": _measure(benchmark_extension_ai_contract, iterations),
            "documents": _measure(benchmark_extension_documents_pipeline, iterations),
        },
        "contours": build_contour_matrix(),
        "matrix": {
            "direct": _measure(benchmark_direct_matrix, iterations),
            "network": build_network_matrix(),
        },
    }
    report["thresholds"] = evaluate_thresholds(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Muscles golden path benchmark")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_benchmarks(iterations=args.iterations)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
        return
    print("Muscles Golden Path Benchmark")
    print(f"iterations={report['iterations']}")
    print(f"thresholds_passed={report['thresholds']['passed']}")
    for key, row in report["golden_path"].items():
        print(f"{key}: avg={row['avg_ms']}ms min={row['min_ms']}ms max={row['max_ms']}ms")
    for section in ("correctness", "architecture", "dx", "streaming", "observability", "transactions", "extensions"):
        for key, row in report[section].items():
            print(f"{section}.{key}: avg={row['avg_ms']}ms result={row['result']}")
    direct = report["matrix"]["direct"]
    print(
        "direct-matrix: "
        f"avg={direct['avg_ms']}ms fair={direct['result']['fair_contour']} contour={direct['result']['contour']}"
    )


if __name__ == "__main__":
    main()
