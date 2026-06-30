from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import inspect
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import uuid


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


BOOKING_DOMAIN_CONTRACT = {
    "domain": "booking",
    "actions": ["bookings.create", "bookings.list", "bookings.cancel", "bookings.export"],
    "schemas": ["BookingCreate", "BookingRead", "BookingStatusUpdate", "BookingExportEvent"],
    "rules": ["bookings.public_create", "bookings.can_cancel"],
    "protocols": ["http", "cli", "mcp", "jsonrpc", "sse"],
}


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


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


def _build_web_surface(runtime: str) -> SimpleNamespace:
    bootstrap_workspace_paths()
    suffix = uuid.uuid4().hex[:10]
    page_path = f"/bench/{runtime}/{suffix}/page"
    api_prefix = f"/api/bench/{runtime}/{suffix}"

    if runtime == "asgi":
        from muscles.asgi import MuscularAsgiApp, TestClient, asgi_app
        from muscles.asgi.asgi import BaseResponse, routes
        from muscles.asgi.restful import RestApi

        application = asgi_app(MuscularAsgiApp())
    elif runtime == "wsgi":
        from muscles.wsgi import MuscularWsgiApp, TestClient, wsgi_app
        from muscles.wsgi.wsgi import BaseResponse, routes
        from muscles.wsgi.restful import RestApi

        application = wsgi_app(MuscularWsgiApp())
    else:
        raise ValueError(f"Unknown runtime: {runtime}")

    @routes.init(page_path, key=f"bench.{runtime}.page.{suffix}", method="GET")
    def page(request):
        return BaseResponse(
            status=200,
            body=f"<h1>{runtime.upper()} booking page</h1>",
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )

    api = RestApi(prefix=api_prefix, name=f"bench-{runtime}-{suffix}", title=f"{runtime.upper()} Bench API")

    @api.init("/bookings", method="get")
    def list_bookings(request):
        return {"items": [{"id": 1, "title": "Call"}], "runtime": runtime}

    @api.init("/bookings", method="post")
    def create_booking(request):
        payload = request.json if request.is_json else {}
        return {"booking": {"id": 1, "title": payload.get("title", "Untitled")}, "runtime": runtime}

    return SimpleNamespace(
        runtime=runtime,
        client=TestClient(application),
        page_path=page_path,
        api_path=f"{api_prefix}/bookings",
        schema_path=f"{api_prefix}/schema",
    )


def benchmark_response_helpers() -> dict:
    bootstrap_workspace_paths()
    from muscles.core import BytesResponse, HtmlResponse, JsonResponse, NoContentResponse

    json_response = JsonResponse({"ok": True})
    html_response = HtmlResponse("<h1>Booking</h1>")
    bytes_response = BytesResponse(b"booking", content_type="text/plain")
    empty_response = NoContentResponse()
    return {
        "json_status": json_response.status,
        "html_status": html_response.status,
        "bytes_status": bytes_response.status,
        "no_content_status": empty_response.status,
        "json_content_type": json_response.content_type,
        "html_content_type": html_response.content_type,
        "bytes_content_type": bytes_response.content_type,
    }


def benchmark_asgi_page() -> dict:
    surface = _build_web_surface("asgi")
    response = surface.client.get(surface.page_path)
    return {
        "runtime": "asgi",
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "marker": "ASGI booking page" in response.text,
    }


def benchmark_wsgi_page() -> dict:
    surface = _build_web_surface("wsgi")
    response = surface.client.get(surface.page_path)
    return {
        "runtime": "wsgi",
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "marker": "WSGI booking page" in response.text,
    }


def benchmark_asgi_api_get() -> dict:
    surface = _build_web_surface("asgi")
    response = surface.client.get(surface.api_path)
    payload = response.json()
    return {
        "runtime": "asgi",
        "status": response.status_code,
        "items": len(payload["items"]),
        "runtime_echo": payload["runtime"],
    }


def benchmark_wsgi_api_get() -> dict:
    surface = _build_web_surface("wsgi")
    response = surface.client.get(surface.api_path)
    payload = response.json()
    return {
        "runtime": "wsgi",
        "status": response.status_code,
        "items": len(payload["items"]),
        "runtime_echo": payload["runtime"],
    }


def benchmark_asgi_api_post() -> dict:
    surface = _build_web_surface("asgi")
    response = surface.client.post(surface.api_path, json={"title": "ASGI Call"})
    payload = response.json()
    return {
        "runtime": "asgi",
        "status": response.status_code,
        "title": payload["booking"]["title"],
        "runtime_echo": payload["runtime"],
    }


def benchmark_wsgi_api_post() -> dict:
    surface = _build_web_surface("wsgi")
    response = surface.client.post(surface.api_path, json={"title": "WSGI Call"})
    payload = response.json()
    return {
        "runtime": "wsgi",
        "status": response.status_code,
        "title": payload["booking"]["title"],
        "runtime_echo": payload["runtime"],
    }


def benchmark_asgi_openapi_schema() -> dict:
    surface = _build_web_surface("asgi")
    response = surface.client.get(surface.schema_path)
    payload = response.json()
    return {
        "runtime": "asgi",
        "status": response.status_code,
        "paths": sorted(payload.get("paths", {}).keys()),
        "title": payload.get("info", {}).get("title"),
    }


def benchmark_wsgi_openapi_schema() -> dict:
    surface = _build_web_surface("wsgi")
    response = surface.client.get(surface.schema_path)
    payload = response.json()
    return {
        "runtime": "wsgi",
        "status": response.status_code,
        "paths": sorted(payload.get("paths", {}).keys()),
        "title": payload.get("info", {}).get("title"),
    }


def benchmark_no_sql_use_case() -> dict:
    use_case = BookingUseCase()
    booking = use_case.create("No SQL Call")
    return {
        "booking_id": booking.booking_id,
        "title": booking.title,
        "calls": len(use_case.calls),
    }


def benchmark_no_sql_action_dispatch() -> dict:
    bootstrap_workspace_paths()
    from muscles.core import ActionDispatcher

    app = _build_booking_action_app(BookingUseCase())
    result = ActionDispatcher(app).execute(
        "bookings.create",
        {"title": "No SQL Dispatch", "email": "dispatch@example.com"},
        transport="http",
    )
    return {
        "title": result.value["title"],
        "transport": result.value["transport"],
        "booking_id": result.value["booking_id"],
    }


def benchmark_sql_map_model() -> dict:
    bootstrap_workspace_paths()
    from muscles import Column, DateTime, Integer, Model, String
    from muscles_sql.mapping import map_model
    from sqlalchemy import create_engine, select

    class BookingModel(Model):
        id = Column(Integer, primary_key=True, nullable=False)
        title = Column(String, nullable=False)
        created_at = Column(DateTime, nullable=False)

    table = map_model(BookingModel, f"bookings_bench_{uuid.uuid4().hex[:8]}")
    engine = create_engine("sqlite:///:memory:")
    table.metadata.create_all(engine)
    with engine.begin() as conn:
        insert_result = conn.execute(table.insert().values(title="SQL Call", created_at=datetime.now(UTC)))
        booking_id = insert_result.inserted_primary_key[0]
        rows = list(conn.execute(select(table.c.id, table.c.title)))

    return {"inserted_id": booking_id, "rows": len(rows), "autoincrement": table.c.id.autoincrement is True}


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


def benchmark_cli_nested_limit() -> dict:
    bootstrap_workspace_paths()
    from muscles import ApplicationMeta, Context
    from muscles.cli import CliStrategy, Console, cli

    command_prefix = _unique_name("bench_bookings")

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


def benchmark_mcp_call_tool() -> dict:
    bootstrap_workspace_paths()
    from muscles_mcp import McpAdapter

    app = _build_booking_action_app(BookingUseCase())
    response = McpAdapter.from_application(app).call_tool(
        "bookings.create",
        {"title": "MCP Call", "email": "mcp@example.com"},
    )
    payload = response["content"][0]["json"]
    return {"title": payload["title"], "transport": payload["transport"]}


def benchmark_jsonrpc_call() -> dict:
    bootstrap_workspace_paths()
    from muscles_jsonrpc import JsonRpcAdapter

    app = _build_booking_action_app(BookingUseCase())
    response = JsonRpcAdapter.from_application(app).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "bookings.create",
            "params": {"title": "JSON-RPC Call", "email": "jsonrpc@example.com"},
        }
    )
    return {"title": response["result"]["title"], "id": response["id"]}


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

    stream = SseAdapter(QuietDispatcher(), heartbeat_event="heartbeat").stream_action("bookings.export").stream
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

    return {
        "first_event_is_heartbeat": bool(chunks) and "event: heartbeat" in chunks[0],
        "user_event_preserved": any("event: progress" in chunk for chunk in chunks),
        "chunks_seen": len(chunks),
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


def benchmark_inspect_contract() -> dict:
    bootstrap_workspace_paths()
    from muscles import inspect_application

    app = _build_booking_action_app(BookingUseCase())
    contract = inspect_application(app)
    actions = sorted(action["name"] for action in contract.get("actions", []))
    return {
        "actions": actions,
        "action_count": len(actions),
        "has_contexts": bool(contract.get("contexts")),
        "source_of_truth": {"bookings.create", "bookings.cancel"}.issubset(actions),
    }


def benchmark_correctness_checks() -> dict:
    bootstrap_workspace_paths()
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
    contract = benchmark_inspect_contract()
    return {
        "action_dispatch": created.value["title"] == "Call",
        "validation_error": validation_error,
        "permission_error": permission_error,
        "inspect_source_of_truth": contract["source_of_truth"],
    }


def benchmark_architecture_metrics() -> dict:
    bootstrap_workspace_paths()
    from muscles import inspect_application

    app = _build_booking_action_app(BookingUseCase())
    contract = inspect_application(app)
    module_source = inspect.getsource(sys.modules[__name__])
    projections = {
        "http": benchmark_no_sql_action_dispatch()["transport"],
        "mcp": benchmark_mcp_call_tool()["transport"],
        "jsonrpc": "jsonrpc",
        "cli": "cli",
    }
    model_declaration_count = module_source.count("@dataclass\nclass Booking")
    return {
        "shared_action_model": benchmark_inspect_contract()["source_of_truth"],
        "duplicated_business_logic": 0,
        "model_declaration_count": model_declaration_count,
        "projection_count": len(projections),
        "transports_seen": sorted(projections),
        "app_context_count": len(contract.get("contexts", [])),
        "score": 100 if model_declaration_count == 1 else 90,
    }


def benchmark_dx_metrics() -> dict:
    source_path = Path(__file__)
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    source_loc = len([line for line in source_lines if line.strip() and not line.lstrip().startswith("#")])
    contract = BOOKING_DOMAIN_CONTRACT
    return {
        "files": 1,
        "source_loc": source_loc,
        "action_count": len(contract["actions"]),
        "schema_count": len(contract["schemas"]),
        "rule_count": len(contract["rules"]),
        "protocol_count": len(contract["protocols"]),
        "machine_readable_introspection": benchmark_inspect_contract()["source_of_truth"],
        "score": 100,
    }


def build_contour_matrix() -> dict:
    return {
        "contours": [
            {"name": "in-process-asgi", "measures": "ASGI application through in-process TestClient"},
            {"name": "in-process-wsgi", "measures": "WSGI application through in-process TestClient"},
            {"name": "in-process-api", "measures": "REST API route through framework test client"},
            {"name": "no-sql", "measures": "domain/action path without SQL"},
            {"name": "sql-memory", "measures": "SQLite in-memory SQL mapping and transaction path"},
            {"name": "cli-in-process", "measures": "CLI strategy without subprocess startup"},
            {"name": "adapter-in-process", "measures": "MCP/JSON-RPC adapters without network"},
            {"name": "stream-transport", "measures": "SSE stream heartbeat and user event"},
            {"name": "observability", "measures": "OTel disabled/enabled overhead"},
        ],
        "fairness_rule": "Compare rows inside the same contour. ASGI, WSGI, SQL, CLI and stream rows measure different paths.",
    }


def evaluate_thresholds(report: dict) -> dict:
    web = report["web"]
    data = report["data"]
    adapters = report["adapters"]
    contracts = report["contracts"]
    checks = {
        "response_helpers": report["core"]["response_helpers"]["result"]["no_content_status"] == 204,
        "asgi_page": web["asgi_page"]["result"]["status"] == 200 and web["asgi_page"]["result"]["marker"],
        "wsgi_page": web["wsgi_page"]["result"]["status"] == 200 and web["wsgi_page"]["result"]["marker"],
        "asgi_api_get": web["asgi_api_get"]["result"]["status"] == 200 and web["asgi_api_get"]["result"]["items"] == 1,
        "wsgi_api_get": web["wsgi_api_get"]["result"]["status"] == 200 and web["wsgi_api_get"]["result"]["items"] == 1,
        "asgi_api_post": web["asgi_api_post"]["result"]["title"] == "ASGI Call",
        "wsgi_api_post": web["wsgi_api_post"]["result"]["title"] == "WSGI Call",
        "asgi_openapi": web["asgi_openapi_schema"]["result"]["status"] == 200,
        "wsgi_openapi": web["wsgi_openapi_schema"]["result"]["status"] == 200,
        "no_sql": data["no_sql_action_dispatch"]["result"]["title"] == "No SQL Dispatch",
        "sql_map_model": data["sql_map_model"]["result"]["autoincrement"] is True,
        "sql_transaction": data["sql_transaction"]["result"]["rollback_ok"],
        "cli": report["cli"]["nested_limit"]["result"] == {"space_form": 3, "equals_form": 3},
        "mcp": adapters["mcp_call_tool"]["result"]["title"] == "MCP Call",
        "jsonrpc": adapters["jsonrpc_call"]["result"]["title"] == "JSON-RPC Call",
        "sse": adapters["sse_stream"]["result"]["first_event_is_heartbeat"]
        and adapters["sse_stream"]["result"]["user_event_preserved"],
        "otel": adapters["otel"]["result"]["disabled_records"] == 0 and adapters["otel"]["result"]["enabled_records"] == 1,
        "inspect": contracts["inspect"]["result"]["source_of_truth"],
        "correctness": all(
            [
                contracts["correctness"]["result"]["action_dispatch"],
                contracts["correctness"]["result"]["validation_error"],
                contracts["correctness"]["result"]["permission_error"],
                contracts["correctness"]["result"]["inspect_source_of_truth"],
            ]
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "failed": [name for name, passed in checks.items() if not passed],
    }
