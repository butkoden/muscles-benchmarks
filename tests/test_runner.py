from muscles_benchmarks.runner import run_benchmarks


def test_benchmark_report_contains_golden_path_and_matrix():
    report = run_benchmarks(iterations=1)
    assert report["iterations"] == 1
    assert "responses" in report["golden_path"]
    assert "openapi_docs_aliases" in report["golden_path"]
    assert "cli_nested_limit" in report["golden_path"]
    assert "sql_map_model" in report["golden_path"]
    assert "direct" in report["matrix"]
    assert "network" in report["matrix"]
    assert report["matrix"]["network"]["servers"][-1]["server"] == "wsgiref"
