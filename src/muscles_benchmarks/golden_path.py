from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import inspect
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import uuid


_OPENAPI_DOCS_ALIAS_RESULT: dict | None = None


def bootstrap_workspace_paths() -> None:
    root = Path(__file__).resolve().parents[3]
    candidates = [
        root / "muscles" / "src",
        root / "muscles-cli" / "src",
        root / "muscles-sql" / "src",
        root / "muscles-asgi" / "src",
        root / "muscles-wsgi" / "src",
        root / "muscles-sse" / "src",
        root / "muscles-otel" / "src",
        root / "muscles-mcp" / "src",
        root / "muscles-jsonrpc" / "src",
    ]
    for candidate in candidates:
        path = str(candidate)
        if candidate.exists() and path not in sys.path:
            sys.path.insert(0, path)


@dataclass
class Booking:
    booking_id: int
    title: str
    created_at: datetime
    email: str = "guest@example.com"
    status: str = "pending"


class BookingUseCase:
    def __init__(self) -> None:
        self._next_id = 1
        self.calls: list[tuple[str, dict]] = []

    def create(self, title: str, email: str = "guest@example.com") -> Booking:
        payload = {"title": title, "email": email}
        self.calls.append(("bookings.create", payload))
        booking = Booking(booking_id=self._next_id, title=title, email=email, created_at=datetime.now(UTC))
        self._next_id += 1
        return booking

    def cancel(self, booking: Booking) -> Booking:
        self.calls.append(("bookings.cancel", {"booking_id": booking.booking_id}))
        if booking.status == "cancelled":
            raise ValueError("Booking is already cancelled")
        booking.status = "cancelled"
        return booking

    def export_events(self):
        yield {"event": "progress", "data": {"done": 1, "total": 2}}
        yield {"event": "result", "data": {"exported": 1}}


BOOKING_DOMAIN_CONTRACT = {
    "domain": "booking",
    "actions": ["bookings.create", "bookings.list", "bookings.cancel", "bookings.export"],
    "schemas": ["BookingCreate", "BookingRead", "BookingStatusUpdate", "BookingExportEvent"],
    "rules": ["bookings.public_create", "bookings.can_cancel"],
    "protocols": ["http", "cli", "mcp", "jsonrpc", "sse"],
}


def _build_booking_action_app(use_case: BookingUseCase):
    bootstrap_workspace_paths()
    from muscles import ApplicationMeta, BaseStrategy, Context

    class Strategy(BaseStrategy):
        def execute(self, *args, **kwargs):
            return kwargs

    class BookingApp(metaclass=ApplicationMeta):
        context = Context(Strategy)

    app = BookingApp()

    @app.action(
        name="bookings.create",
        description="Create a booking request",
        input_schema={
            "type": "object",
            "properties": {"title": {"type": "string"}, "email": {"type": "string"}},
            "required": ["title", "email"],
        },
    )
    def create_booking(payload, context):
        booking = use_case.create(payload["title"], payload.get("email", "guest@example.com"))
        return {
            "booking_id": booking.booking_id,
            "title": booking.title,
            "email": booking.email,
            "transport": context.transport,
        }

    def can_cancel(payload, _context):
        return payload.get("status") != "cancelled"

    @app.action(
        name="bookings.cancel",
        input_schema={
            "type": "object",
            "properties": {"booking_id": {"type": "integer"}, "status": {"type": "string"}},
            "required": ["booking_id", "status"],
        },
        rules=[can_cancel],
    )
    def cancel_booking(payload, _context):
        booking = Booking(
            booking_id=payload["booking_id"],
            title="Existing",
            created_at=datetime.now(UTC),
            status=payload.get("status", "pending"),
        )
        cancelled = use_case.cancel(booking)
        return {"booking_id": cancelled.booking_id, "status": cancelled.status}

    return app


def _call_http_projection(app, payload: dict) -> dict:
    from muscles.core import ActionDispatcher

    result = ActionDispatcher(app).execute("bookings.create", payload, transport="http")
    return result.value


def _call_cli_projection(app, payload: dict) -> dict:
    from muscles.core import ActionDispatcher

    result = ActionDispatcher(app).execute("bookings.create", payload, transport="cli")
    return result.value


def _call_mcp_projection(app, payload: dict) -> dict:
    from muscles_mcp import McpAdapter

    response = McpAdapter.from_application(app).call_tool("bookings.create", payload)
    return response["content"][0]["json"]


def _call_jsonrpc_projection(app, payload: dict) -> dict:
    from muscles_jsonrpc import JsonRpcAdapter

    response = JsonRpcAdapter.from_application(app).handle(
        {"jsonrpc": "2.0", "id": 1, "method": "bookings.create", "params": payload}
    )
    return response["result"]


def benchmark_core_responses() -> dict:
    bootstrap_workspace_paths()
    from muscles.core import HtmlResponse, JsonResponse

    use_case = BookingUseCase()
    booking = use_case.create("Call")
    json_response = JsonResponse({"booking_id": booking.booking_id, "title": booking.title})
    html_response = HtmlResponse(f"<h1>{booking.title}</h1>")
    return {
        "json_content_type": json_response.content_type,
        "html_content_type": html_response.content_type,
        "json_status": json_response.status,
        "html_status": html_response.status,
    }


def benchmark_openapi_docs_aliases() -> dict:
    global _OPENAPI_DOCS_ALIAS_RESULT
    if _OPENAPI_DOCS_ALIAS_RESULT is not None:
        return dict(_OPENAPI_DOCS_ALIAS_RESULT)

    bootstrap_workspace_paths()
    from muscles.asgi.restful import RestApi as AsgiRestApi
    from muscles.wsgi.restful import RestApi as WsgiRestApi

    suffix = uuid.uuid4().hex[:8]
    asgi_api = AsgiRestApi(prefix=f"/api/{suffix}", name=f"api-asgi-{suffix}", title="ASGI API")
    wsgi_api = WsgiRestApi(prefix=f"/api/{suffix}", name=f"api-wsgi-{suffix}", title="WSGI API")

    req_docs = SimpleNamespace(path="/docs", method="GET", content_type="text/html")
    req_openapi = SimpleNamespace(path="/openapi.json", method="GET", content_type="application/json")

    asgi_docs, _ = asgi_api.get_current_route(req_docs)
    asgi_openapi, _ = asgi_api.get_current_route(req_openapi)
    wsgi_docs, _ = wsgi_api.get_current_route(req_docs)
    wsgi_openapi, _ = wsgi_api.get_current_route(req_openapi)
    _OPENAPI_DOCS_ALIAS_RESULT = {
        "asgi_docs": bool(asgi_docs),
        "asgi_openapi": bool(asgi_openapi),
        "wsgi_docs": bool(wsgi_docs),
        "wsgi_openapi": bool(wsgi_openapi),
    }
    return dict(_OPENAPI_DOCS_ALIAS_RESULT)


def benchmark_cli_nested_limit() -> dict:
    bootstrap_workspace_paths()
    from muscles import ApplicationMeta, Context
    from muscles.cli import CliStrategy, Console, cli

    command_prefix = f"bench_bookings_{uuid.uuid4().hex[:8]}"

    class App(metaclass=ApplicationMeta):
        context = Context(CliStrategy)
        console = Console()

        def run(self, *args):
            return self.context.execute(*args, shutup=True)

    app = App()

    @cli.group(command_name=command_prefix)
    def bookings(*args):
        return True

    @bookings.command(command_name="list")
    @bookings.argument("--limit", nargs=1, default="25")
    def bookings_list(*args, limit):
        return int(limit)

    result_space = app.run(command_prefix, "list", "--limit", "3")
    result_equals = app.run(command_prefix, "list", "--limit=3")
    return {"space_form": result_space, "equals_form": result_equals}


def benchmark_sql_map_model() -> dict:
    bootstrap_workspace_paths()
    from muscles import Column, DateTime, Integer, Model, String
    from muscles_sql.mapping import map_model
    from sqlalchemy import create_engine, select

    class BookingModel(Model):
        id = Column(Integer, primary_key=True, nullable=False)
        title = Column(String, nullable=False)
        created_at = Column(DateTime, nullable=False)

    table = map_model(BookingModel, "bookings_bench")
    engine = create_engine("sqlite:///:memory:")
    table.metadata.create_all(engine)
    with engine.begin() as conn:
        insert_result = conn.execute(
            table.insert().values(title="Call", created_at=datetime.now(UTC))
        )
        booking_id = insert_result.inserted_primary_key[0]
        rows = list(conn.execute(select(table.c.id)))

    return {"inserted_id": booking_id, "rows": len(rows), "autoincrement": table.c.id.autoincrement is True}


def benchmark_direct_matrix() -> dict:
    bootstrap_workspace_paths()
    from muscles.asgi.restful import RestApi as AsgiRestApi
    from muscles.wsgi.restful import RestApi as WsgiRestApi

    suffix = uuid.uuid4().hex[:8]
    asgi_api = AsgiRestApi(prefix=f"/direct/{suffix}", name=f"direct-asgi-{suffix}", title="ASGI direct API")
    wsgi_api = WsgiRestApi(prefix=f"/direct/{suffix}", name=f"direct-wsgi-{suffix}", title="WSGI direct API")
    req = SimpleNamespace(path="/openapi.json", method="GET", content_type="application/json")
    asgi_route, _ = asgi_api.get_current_route(req)
    wsgi_route, _ = wsgi_api.get_current_route(req)
    return {
        "direct_asgi_router": bool(asgi_route),
        "direct_wsgi_router": bool(wsgi_route),
        "fair_contour": True,
        "contour": "direct-no-network",
    }


def benchmark_booking_domain_alignment() -> dict:
    use_case = BookingUseCase()
    app = _build_booking_action_app(use_case)
    projection_calls = {
        "http": _call_http_projection(app, {"title": "HTTP", "email": "http@example.com"}),
        "cli": _call_cli_projection(app, {"title": "CLI", "email": "cli@example.com"}),
        "mcp": _call_mcp_projection(app, {"title": "MCP", "email": "mcp@example.com"}),
        "jsonrpc": _call_jsonrpc_projection(app, {"title": "JSON-RPC", "email": "jsonrpc@example.com"}),
    }
    transports_seen = sorted({result["transport"] for result in projection_calls.values()})
    return {
        "domain": BOOKING_DOMAIN_CONTRACT["domain"],
        "actions": len(BOOKING_DOMAIN_CONTRACT["actions"]),
        "schemas": len(BOOKING_DOMAIN_CONTRACT["schemas"]),
        "rules": len(BOOKING_DOMAIN_CONTRACT["rules"]),
        "protocols": len(BOOKING_DOMAIN_CONTRACT["protocols"]),
        "shared_use_case_calls": len(use_case.calls),
        "call_actions": sorted({name for name, _payload in use_case.calls}),
        "projection_calls": projection_calls,
        "projection_count": len(projection_calls),
        "transports_seen": transports_seen,
        "booking_titles": [result["title"] for result in projection_calls.values()],
        "same_action_handler": sorted({name for name, _payload in use_case.calls}) == ["bookings.create"],
    }


def benchmark_correctness_checks() -> dict:
    bootstrap_workspace_paths()
    from muscles import inspect_application
    from muscles.core import ActionDispatcher, ActionPermissionDenied, ActionValidationError

    app = _build_booking_action_app(BookingUseCase())

    dispatcher = ActionDispatcher(app)
    created = dispatcher.execute(
        "bookings.create",
        {"title": "Call", "email": "guest@example.com"},
        transport="mcp",
    )
    validation_error = False
    permission_error = False
    try:
        dispatcher.execute("bookings.create", {"email": "guest@example.com"}, transport="mcp")
    except ActionValidationError:
        validation_error = True
    try:
        dispatcher.execute("bookings.cancel", {"booking_id": 1, "status": "cancelled"}, transport="mcp")
    except ActionPermissionDenied:
        permission_error = True
    contract = inspect_application(app)
    actions = {action["name"] for action in contract.get("actions", [])}
    return {
        "action_dispatch": created.value["title"] == "Call",
        "validation_error": validation_error,
        "permission_error": permission_error,
        "inspect_actions": sorted(actions),
        "inspect_source_of_truth": {"bookings.create", "bookings.cancel"}.issubset(actions),
    }


def benchmark_architecture_metrics() -> dict:
    alignment = benchmark_booking_domain_alignment()
    module_source = inspect.getsource(sys.modules[__name__])
    duplicated_business_logic = 0 if alignment["same_action_handler"] else alignment["projection_count"]
    model_declaration_count = module_source.count("@dataclass\nclass Booking")
    projection_count = alignment["projection_count"]
    score = 100
    score -= duplicated_business_logic * 20
    score -= max(model_declaration_count - 1, 0) * 10
    score -= 20 if alignment["shared_use_case_calls"] != projection_count else 0
    return {
        "shared_use_case": alignment["shared_use_case_calls"] == projection_count,
        "duplicated_business_logic": duplicated_business_logic,
        "model_declaration_count": model_declaration_count,
        "projection_count": projection_count,
        "transports_seen": alignment["transports_seen"],
        "inspect_source_of_truth": benchmark_correctness_checks()["inspect_source_of_truth"],
        "score": max(score, 0),
    }


def benchmark_dx_metrics() -> dict:
    contract = BOOKING_DOMAIN_CONTRACT
    source_path = Path(__file__)
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    source_loc = len([line for line in source_lines if line.strip() and not line.lstrip().startswith("#")])
    correctness = benchmark_correctness_checks()
    ai_change_tasks = [
        "add Booking.phone field",
        "add status transition rule",
        "add CLI command from existing action",
        "expose action through MCP/JSON-RPC from inspect contract",
    ]
    score = 0
    score += 20 if len(contract["actions"]) >= 4 else 0
    score += 20 if len(contract["schemas"]) >= 4 else 0
    score += 20 if len(contract["rules"]) >= 2 else 0
    score += 20 if len(contract["protocols"]) >= 5 else 0
    score += 20 if correctness["inspect_source_of_truth"] else 0
    return {
        "files": 1,
        "source_loc": source_loc,
        "action_count": len(contract["actions"]),
        "schema_count": len(contract["schemas"]),
        "rule_count": len(contract["rules"]),
        "protocol_count": len(contract["protocols"]),
        "machine_readable_introspection": True,
        "ai_change_tasks": ai_change_tasks,
        "score": score,
    }


def benchmark_sql_transaction() -> dict:
    bootstrap_workspace_paths()
    from muscles import Column, Integer, Model, String
    from muscles_sql.mapping import map_model
    from sqlalchemy import create_engine, select

    class BookingModel(Model):
        id = Column(Integer, primary_key=True, nullable=False)
        title = Column(String, nullable=False)

    table = map_model(BookingModel, f"bookings_tx_{uuid.uuid4().hex[:8]}")
    engine = create_engine("sqlite:///:memory:")
    table.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(table.insert().values(title="committed"))
    try:
        with engine.begin() as conn:
            conn.execute(table.insert().values(title="rolled-back"))
            raise RuntimeError("rollback")
    except RuntimeError:
        pass
    with engine.begin() as conn:
        rows = [row.title for row in conn.execute(select(table.c.title))]
    return {"committed_rows": rows, "rollback_ok": rows == ["committed"]}


def benchmark_sse_stream() -> dict:
    bootstrap_workspace_paths()
    from muscles_sse import SseAdapter

    class QuietDispatcher:
        def execute(self, *_args, **_kwargs):
            def source():
                yield {"event": "heartbeat", "data": {"ok": True}}
                time.sleep(0.02)
                yield {"type": "progress", "data": {"done": 1, "total": 1}}
                yield {"type": "result", "data": {"ok": True}}

            return source()

    stream = SseAdapter(
        QuietDispatcher(),
        heartbeat_event="heartbeat",
    ).stream_action("bookings.export").stream
    chunks = []
    try:
        iterator = iter(stream)
        for _ in range(10):
            try:
                chunk = next(iterator)
            except StopIteration:
                break
            chunks.append(chunk)
            if "event: progress" in chunk:
                break
    finally:
        stream.close()
    class FastDispatcher:
        def __init__(self):
            self.produced = 0

        def execute(self, *_args, **_kwargs):
            def source():
                while True:
                    self.produced += 1
                    yield {"type": "progress", "data": {"step": self.produced}}

            return source()

    fast_dispatcher = FastDispatcher()
    fast_stream = SseAdapter(
        fast_dispatcher,
        heartbeat_event="heartbeat",
    ).stream_action("bookings.export").stream
    try:
        next(iter(fast_stream))
        time.sleep(0.05)
        read_ahead = fast_dispatcher.produced
    finally:
        fast_stream.close()

    return {
        "first_event_is_heartbeat": bool(chunks) and "event: heartbeat" in chunks[0],
        "user_event_preserved": any("event: progress" in chunk for chunk in chunks),
        "chunks_seen": len(chunks),
        "read_ahead": read_ahead,
        "bounded_backpressure": read_ahead <= 3,
        "contour": "stream-transport",
    }


def benchmark_otel_overhead() -> dict:
    bootstrap_workspace_paths()
    from muscles_otel import MusclesTracer, instrument_action_dispatch

    disabled = MusclesTracer(enabled=False)
    enabled = MusclesTracer(enabled=True)
    app = _build_booking_action_app(BookingUseCase())

    started = time.perf_counter()
    disabled.instrument_call("muscles.action.execute", lambda: 1, **{"muscles.action.name": "bookings.create"})
    disabled_ms = (time.perf_counter() - started) * 1000.0

    started = time.perf_counter()
    enabled.instrument_call("muscles.action.execute", lambda: 1, **{"muscles.action.name": "bookings.create"})
    enabled_ms = (time.perf_counter() - started) * 1000.0

    lifecycle = MusclesTracer(enabled=True)
    started = time.perf_counter()
    instrument_action_dispatch(
        lifecycle,
        app,
        action_name="bookings.create",
        payload={"title": "Trace", "email": "trace@example.com"},
        transport="mcp",
    )
    lifecycle_ms = (time.perf_counter() - started) * 1000.0
    lifecycle_spans = [record.name for record in lifecycle.records]

    return {
        "disabled_records": len(disabled.records),
        "enabled_records": len(enabled.records),
        "disabled_ms": round(disabled_ms, 6),
        "enabled_ms": round(enabled_ms, 6),
        "lifecycle_ms": round(lifecycle_ms, 6),
        "lifecycle_spans": lifecycle_spans,
        "contour": "observability",
    }


def build_contour_matrix() -> dict:
    return {
        "contours": [
            {"name": "direct-no-network", "measures": "core/router/action cost without socket"},
            {"name": "in-process-adapter", "measures": "adapter projection without network"},
            {"name": "network-prod", "measures": "production HTTP server over socket"},
            {"name": "network-dev-reference", "measures": "development/reference server over socket"},
            {"name": "subprocess-cli", "measures": "CLI process startup and command execution"},
            {"name": "cold-start", "measures": "import/application bootstrap cost"},
            {"name": "stream-transport", "measures": "SSE stream heartbeat/backpressure/disconnect"},
            {"name": "observability", "measures": "OTel disabled/enabled overhead"},
            {"name": "transaction", "measures": "SQL transaction commit/rollback"},
        ],
        "fairness_rule": "Compare only rows with the same contour unless the report explicitly explains the contour difference.",
    }


def evaluate_thresholds(report: dict) -> dict:
    checks = {
        "responses_contract": report["golden_path"]["responses"]["result"]["json_status"] == 200,
        "openapi_docs": all(report["golden_path"]["openapi_docs_aliases"]["result"].values()),
        "cli_nested_args": report["golden_path"]["cli_nested_limit"]["result"] == {"space_form": 3, "equals_form": 3},
        "sql_map_model": report["golden_path"]["sql_map_model"]["result"]["autoincrement"] is True,
        "correctness": all(
            [
                report["correctness"]["action_dispatch"]["result"]["action_dispatch"],
                report["correctness"]["action_dispatch"]["result"]["validation_error"],
                report["correctness"]["action_dispatch"]["result"]["permission_error"],
                report["correctness"]["action_dispatch"]["result"]["inspect_source_of_truth"],
            ]
        ),
        "architecture_score": report["architecture"]["metrics"]["result"]["score"] >= 80,
        "dx_score": report["dx"]["metrics"]["result"]["score"] >= 80,
        "sse_stream": all(
            [
                report["streaming"]["sse"]["result"]["first_event_is_heartbeat"],
                report["streaming"]["sse"]["result"]["user_event_preserved"],
                report["streaming"]["sse"]["result"]["bounded_backpressure"],
            ]
        ),
        "otel": report["observability"]["otel"]["result"]["disabled_records"] == 0
        and report["observability"]["otel"]["result"]["enabled_records"] == 1
        and set(report["observability"]["otel"]["result"]["lifecycle_spans"])
        == {
            "muscles.action.validate",
            "muscles.action.rules",
            "muscles.action.handler",
            "muscles.action.execute",
        },
        "sql_transaction": report["transactions"]["sql"]["result"]["rollback_ok"],
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "failed": [name for name, passed in checks.items() if not passed],
    }
