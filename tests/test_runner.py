from muscles_benchmarks.runner import run_benchmarks


def test_benchmark_report_contains_golden_path_and_matrix():
    report = run_benchmarks(iterations=1)
    assert report["iterations"] == 1
    assert report["booking_domain"]["result"]["domain"] == "booking"
    assert "responses" in report["golden_path"]
    assert "openapi_docs_aliases" in report["golden_path"]
    assert "cli_nested_limit" in report["golden_path"]
    assert "sql_map_model" in report["golden_path"]
    assert "action_dispatch" in report["correctness"]
    assert "metrics" in report["architecture"]
    assert "metrics" in report["dx"]
    assert "sse" in report["streaming"]
    assert "otel" in report["observability"]
    assert "sql" in report["transactions"]
    assert "ai" in report["extensions"]
    assert "documents" in report["extensions"]
    assert report["extensions"]["ai"]["result"]["runtime_provider"] == "noop"
    assert report["extensions"]["documents"]["result"]["request_status"] == "planned"
    assert report["package_matrix"]["result"]["all_imports"] is True
    assert len(report["package_matrix"]["result"]["memory_adapters"]) >= 6
    assert "thresholds" in report
    assert "direct" in report["matrix"]
    assert "network" in report["matrix"]
    assert report["matrix"]["network"]["servers"][-1]["server"] == "wsgiref"


def test_benchmark_report_contains_fair_contours():
    report = run_benchmarks(iterations=1)
    contours = {row["name"] for row in report["contours"]["contours"]}
    assert {
        "direct-no-network",
        "in-process-adapter",
        "network-prod",
        "network-dev-reference",
        "subprocess-cli",
        "cold-start",
        "stream-transport",
        "observability",
        "transaction",
    }.issubset(contours)


def test_benchmark_thresholds_pass_for_current_golden_path():
    report = run_benchmarks(iterations=1)
    assert report["thresholds"]["passed"] is True
    assert report["thresholds"]["failed"] == []
