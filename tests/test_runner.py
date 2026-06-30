from muscles_benchmarks.runner import run_benchmarks


def test_benchmark_report_contains_lightweight_measurement_matrix():
    report = run_benchmarks(iterations=1)

    assert report["iterations"] == 1
    assert "response_helpers" in report["core"]
    assert "asgi_page" in report["web"]
    assert "wsgi_page" in report["web"]
    assert "asgi_api_get" in report["web"]
    assert "wsgi_api_get" in report["web"]
    assert "asgi_api_post" in report["web"]
    assert "wsgi_api_post" in report["web"]
    assert "asgi_openapi_schema" in report["web"]
    assert "wsgi_openapi_schema" in report["web"]
    assert "no_sql_use_case" in report["data"]
    assert "no_sql_action_dispatch" in report["data"]
    assert "sql_map_model" in report["data"]
    assert "sql_transaction" in report["data"]
    assert "nested_limit" in report["cli"]
    assert "mcp_call_tool" in report["adapters"]
    assert "jsonrpc_call" in report["adapters"]
    assert "sse_stream" in report["adapters"]
    assert "otel" in report["adapters"]
    assert "inspect" in report["contracts"]
    assert "correctness" in report["contracts"]
    assert "architecture" in report["contracts"]
    assert "dx" in report["contracts"]
    assert "thresholds" in report


def test_benchmark_report_contains_fair_contours():
    report = run_benchmarks(iterations=1)
    contours = {row["name"] for row in report["contours"]["contours"]}
    assert {
        "in-process-asgi",
        "in-process-wsgi",
        "in-process-api",
        "no-sql",
        "sql-memory",
        "cli-in-process",
        "adapter-in-process",
        "stream-transport",
        "observability",
    }.issubset(contours)


def test_benchmark_thresholds_pass_for_current_matrix():
    report = run_benchmarks(iterations=1)
    assert report["thresholds"]["passed"] is True
    assert report["thresholds"]["failed"] == []
