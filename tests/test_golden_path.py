from muscles_benchmarks.golden_path import (
    benchmark_architecture_metrics,
    benchmark_asgi_api_get,
    benchmark_asgi_api_post,
    benchmark_asgi_openapi_schema,
    benchmark_asgi_page,
    benchmark_cli_nested_limit,
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
)


def test_core_response_helpers_are_real_contract():
    result = benchmark_response_helpers()
    assert result["json_content_type"].startswith("application/json")
    assert result["html_content_type"].startswith("text/html")
    assert result["bytes_content_type"] == "text/plain"
    assert result["no_content_status"] == 204


def test_pages_are_measured_separately_for_asgi_and_wsgi():
    asgi = benchmark_asgi_page()
    wsgi = benchmark_wsgi_page()

    assert asgi["runtime"] == "asgi"
    assert wsgi["runtime"] == "wsgi"
    assert asgi["status"] == 200
    assert wsgi["status"] == 200
    assert asgi["marker"] is True
    assert wsgi["marker"] is True


def test_api_get_is_measured_separately_for_asgi_and_wsgi():
    asgi = benchmark_asgi_api_get()
    wsgi = benchmark_wsgi_api_get()

    assert asgi["runtime_echo"] == "asgi"
    assert wsgi["runtime_echo"] == "wsgi"
    assert asgi["status"] == 200
    assert wsgi["status"] == 200
    assert asgi["items"] == 1
    assert wsgi["items"] == 1


def test_api_post_is_measured_separately_for_asgi_and_wsgi():
    asgi = benchmark_asgi_api_post()
    wsgi = benchmark_wsgi_api_post()

    assert asgi["status"] == 200
    assert wsgi["status"] == 200
    assert asgi["title"] == "ASGI Call"
    assert wsgi["title"] == "WSGI Call"


def test_openapi_schema_is_measured_separately_for_asgi_and_wsgi():
    asgi = benchmark_asgi_openapi_schema()
    wsgi = benchmark_wsgi_openapi_schema()

    assert asgi["status"] == 200
    assert wsgi["status"] == 200
    assert asgi["title"].startswith("ASGI")
    assert wsgi["title"].startswith("WSGI")
    assert any(path.endswith("/bookings") for path in asgi["paths"])
    assert any(path.endswith("/bookings") for path in wsgi["paths"])


def test_no_sql_and_sql_paths_are_separate():
    use_case = benchmark_no_sql_use_case()
    dispatch = benchmark_no_sql_action_dispatch()
    sql_map = benchmark_sql_map_model()
    tx = benchmark_sql_transaction()

    assert use_case["title"] == "No SQL Call"
    assert dispatch["title"] == "No SQL Dispatch"
    assert sql_map["autoincrement"] is True
    assert sql_map["rows"] == 1
    assert tx["rollback_ok"] is True
    assert tx["committed_rows"] == ["committed"]


def test_cli_nested_limit_both_forms():
    result = benchmark_cli_nested_limit()
    assert result["space_form"] == 3
    assert result["equals_form"] == 3


def test_protocol_adapters_are_measured():
    mcp = benchmark_mcp_call_tool()
    jsonrpc = benchmark_jsonrpc_call()
    sse = benchmark_sse_stream()
    otel = benchmark_otel_overhead()

    assert mcp["title"] == "MCP Call"
    assert mcp["transport"] == "mcp"
    assert jsonrpc["title"] == "JSON-RPC Call"
    assert jsonrpc["id"] == 1
    assert sse["first_event_is_heartbeat"] is True
    assert sse["user_event_preserved"] is True
    assert otel["disabled_records"] == 0
    assert otel["enabled_records"] == 1


def test_contracts_correctness_architecture_and_dx_are_still_visible():
    inspect_contract = benchmark_inspect_contract()
    correctness = benchmark_correctness_checks()
    architecture = benchmark_architecture_metrics()
    dx = benchmark_dx_metrics()

    assert inspect_contract["source_of_truth"] is True
    assert correctness["action_dispatch"] is True
    assert correctness["validation_error"] is True
    assert correctness["permission_error"] is True
    assert architecture["duplicated_business_logic"] == 0
    assert architecture["score"] >= 80
    assert dx["machine_readable_introspection"] is True
    assert dx["score"] >= 80
