from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from statistics import mean
from time import perf_counter

from .golden_path import (
    benchmark_architecture_metrics,
    benchmark_cli_nested_limit,
    benchmark_asgi_api_get,
    benchmark_asgi_api_post,
    benchmark_asgi_openapi_schema,
    benchmark_asgi_page,
    benchmark_correctness_checks,
    benchmark_dx_metrics,
    benchmark_inspect_contract,
    benchmark_jsonrpc_call,
    benchmark_mcp_call_tool,
    benchmark_no_sql_action_dispatch,
    benchmark_no_sql_use_case,
    benchmark_otel_overhead,
    benchmark_response_helpers,
    benchmark_sql_map_model,
    benchmark_sql_transaction,
    benchmark_sse_stream,
    benchmark_wsgi_api_get,
    benchmark_wsgi_api_post,
    benchmark_wsgi_openapi_schema,
    benchmark_wsgi_page,
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
            },
        },
        "core": {
            "response_helpers": _measure(benchmark_response_helpers, iterations),
        },
        "web": {
            "asgi_page": _measure(benchmark_asgi_page, iterations),
            "wsgi_page": _measure(benchmark_wsgi_page, iterations),
            "asgi_api_get": _measure(benchmark_asgi_api_get, iterations),
            "wsgi_api_get": _measure(benchmark_wsgi_api_get, iterations),
            "asgi_api_post": _measure(benchmark_asgi_api_post, iterations),
            "wsgi_api_post": _measure(benchmark_wsgi_api_post, iterations),
            "asgi_openapi_schema": _measure(benchmark_asgi_openapi_schema, iterations),
            "wsgi_openapi_schema": _measure(benchmark_wsgi_openapi_schema, iterations),
        },
        "data": {
            "no_sql_use_case": _measure(benchmark_no_sql_use_case, iterations),
            "no_sql_action_dispatch": _measure(benchmark_no_sql_action_dispatch, iterations),
            "sql_map_model": _measure(benchmark_sql_map_model, iterations),
            "sql_transaction": _measure(benchmark_sql_transaction, iterations),
        },
        "cli": {
            "nested_limit": _measure(benchmark_cli_nested_limit, iterations),
        },
        "adapters": {
            "mcp_call_tool": _measure(benchmark_mcp_call_tool, iterations),
            "jsonrpc_call": _measure(benchmark_jsonrpc_call, iterations),
            "sse_stream": _measure(benchmark_sse_stream, iterations),
            "otel": _measure(benchmark_otel_overhead, iterations),
        },
        "contracts": {
            "inspect": _measure(benchmark_inspect_contract, iterations),
            "correctness": _measure(benchmark_correctness_checks, iterations),
            "architecture": _measure(benchmark_architecture_metrics, iterations),
            "dx": _measure(benchmark_dx_metrics, iterations),
        },
        "contours": build_contour_matrix(),
        "network_matrix": build_network_matrix(),
    }
    report["thresholds"] = evaluate_thresholds(report)
    return report


def _print_section(title: str, rows: dict) -> None:
    print(title)
    for key, row in rows.items():
        print(
            f"  {key}: avg={row['avg_ms']}ms min={row['min_ms']}ms max={row['max_ms']}ms "
            f"result={row['result']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Muscles golden path benchmark")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_benchmarks(iterations=args.iterations)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
        return
    print("Muscles Lightweight Benchmark Matrix")
    print(f"iterations={report['iterations']}")
    print(f"thresholds_passed={report['thresholds']['passed']}")
    _print_section("core", report["core"])
    _print_section("web", report["web"])
    _print_section("data", report["data"])
    _print_section("cli", report["cli"])
    _print_section("adapters", report["adapters"])
    _print_section("contracts", report["contracts"])


if __name__ == "__main__":
    main()
