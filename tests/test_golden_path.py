from muscles_benchmarks.golden_path import (
    benchmark_architecture_metrics,
    benchmark_booking_domain_alignment,
    benchmark_cli_nested_limit,
    benchmark_core_responses,
    benchmark_correctness_checks,
    benchmark_direct_matrix,
    benchmark_dx_metrics,
    benchmark_otel_overhead,
    benchmark_openapi_docs_aliases,
    benchmark_sql_transaction,
    benchmark_sql_map_model,
    benchmark_sse_stream,
)


def test_core_response_helpers_are_real_contract():
    result = benchmark_core_responses()
    assert result["json_content_type"].startswith("application/json")
    assert result["html_content_type"].startswith("text/html")


def test_openapi_docs_aliases_exist_for_asgi_and_wsgi():
    result = benchmark_openapi_docs_aliases()
    assert result == {
        "asgi_docs": True,
        "asgi_openapi": True,
        "wsgi_docs": True,
        "wsgi_openapi": True,
    }


def test_cli_nested_limit_both_forms():
    result = benchmark_cli_nested_limit()
    assert result["space_form"] == 3
    assert result["equals_form"] == 3


def test_sql_map_model_with_real_muscles_columns():
    result = benchmark_sql_map_model()
    assert result["autoincrement"] is True
    assert result["inserted_id"] is not None
    assert result["rows"] == 1


def test_direct_matrix_has_fair_contour():
    result = benchmark_direct_matrix()
    assert result["direct_asgi_router"] is True
    assert result["direct_wsgi_router"] is True
    assert result["fair_contour"] is True


def test_booking_domain_alignment_uses_shared_use_case():
    result = benchmark_booking_domain_alignment()
    assert result["domain"] == "booking"
    assert result["actions"] >= 4
    assert result["protocols"] >= 5
    assert result["shared_use_case_calls"] == 4
    assert result["call_actions"] == ["bookings.create"]


def test_correctness_checks_cover_validation_rules_and_inspect():
    result = benchmark_correctness_checks()
    assert result["action_dispatch"] is True
    assert result["validation_error"] is True
    assert result["permission_error"] is True
    assert result["inspect_source_of_truth"] is True


def test_architecture_and_dx_scores_are_high_enough():
    architecture = benchmark_architecture_metrics()
    dx = benchmark_dx_metrics()
    assert architecture["shared_use_case"] is True
    assert architecture["duplicated_business_logic"] == 0
    assert architecture["score"] >= 80
    assert dx["machine_readable_introspection"] is True
    assert dx["score"] >= 80


def test_sse_stream_and_otel_overhead_are_measured():
    sse = benchmark_sse_stream()
    otel = benchmark_otel_overhead()
    assert sse["first_event_is_heartbeat"] is True
    assert sse["user_event_preserved"] is True
    assert otel["disabled_records"] == 0
    assert otel["enabled_records"] == 1


def test_sql_transaction_rolls_back_failed_unit():
    result = benchmark_sql_transaction()
    assert result["rollback_ok"] is True
    assert result["committed_rows"] == ["committed"]


def test_benchmark_contract_reports_transport_linked_contexts():
    from muscles import ApplicationMeta, BaseStrategy, Context, inspect_application

    class _Strategy(BaseStrategy):
        def execute(self, *args, **kwargs):
            return kwargs

    class _App(metaclass=ApplicationMeta):
        context = Context(_Strategy)
        asgi_public = Context(_Strategy, params={"profile": "public"})
        asgi_admin = Context(_Strategy, params={"profile": "admin"})
        mcp_public = Context(_Strategy, transport=asgi_public, params={"mcp_profile": "public"})
        mcp_admin = Context(_Strategy, transport=asgi_admin, params={"mcp_profile": "admin"})

    app = _App()
    contract = inspect_application(app)
    by_name = {item["name"]: item for item in contract["contexts"]}

    assert set(by_name) == {"context", "asgi_public", "asgi_admin", "mcp_public", "mcp_admin"}
    assert by_name["mcp_admin"]["transport"] == "asgi_admin"
    assert by_name["mcp_public"]["transport"] == "asgi_public"
    assert by_name["mcp_admin"]["transport"] == "asgi_admin"
    assert by_name["context"]["strategy"] == "_Strategy"
