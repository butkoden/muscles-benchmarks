from __future__ import annotations

import argparse
import json
from statistics import mean
from time import perf_counter

from .app import BookingApp


def _measure(callback, iterations: int) -> dict:
    samples = []
    for _ in range(iterations):
        started = perf_counter()
        callback()
        samples.append((perf_counter() - started) * 1000.0)
    return {"avg_ms": round(mean(samples), 6), "min_ms": round(min(samples), 6), "max_ms": round(max(samples), 6)}


def run_benchmarks(iterations: int = 1000) -> dict:
    app = BookingApp()
    return {
        "iterations": iterations,
        "api": _measure(lambda: app.api_create_booking({"title": "Call"}), iterations),
        "cli": _measure(lambda: app.cli_bookings_create("Call"), iterations),
        "sql": _measure(lambda: app.sql_insert_booking("Call"), iterations),
        "action": _measure(lambda: app.action_call("bookings.create", {"title": "Call"}), iterations),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Muscles golden path benchmark")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_benchmarks(iterations=args.iterations)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
        return
    print("Muscles Golden Path Benchmark")
    print(f"iterations={report['iterations']}")
    for key in ("api", "cli", "sql", "action"):
        row = report[key]
        print(f"{key}: avg={row['avg_ms']}ms min={row['min_ms']}ms max={row['max_ms']}ms")


if __name__ == "__main__":
    main()
