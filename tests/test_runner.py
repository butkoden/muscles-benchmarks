from muscles_benchmarks import run_benchmarks


def test_benchmark_report_shape():
    report = run_benchmarks(iterations=25)
    assert report["iterations"] == 25
    for part in ("api", "cli", "sql", "action"):
        assert "avg_ms" in report[part]
        assert "min_ms" in report[part]
        assert "max_ms" in report[part]
