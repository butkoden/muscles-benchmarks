from muscles_benchmarks.golden_path import (
    benchmark_cli_nested_limit,
    benchmark_core_responses,
    benchmark_direct_matrix,
    benchmark_openapi_docs_aliases,
    benchmark_sql_map_model,
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
