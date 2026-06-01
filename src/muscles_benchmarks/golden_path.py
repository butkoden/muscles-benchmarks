from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import sys
import uuid


def bootstrap_workspace_paths() -> None:
    root = Path(__file__).resolve().parents[3]
    candidates = [
        root / "muscles" / "src",
        root / "muscles-cli" / "src",
        root / "muscles-sql" / "src",
        root / "muscles-asgi" / "src",
        root / "muscles-wsgi" / "src",
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


class BookingUseCase:
    def __init__(self) -> None:
        self._next_id = 1

    def create(self, title: str) -> Booking:
        booking = Booking(booking_id=self._next_id, title=title, created_at=datetime.now(UTC))
        self._next_id += 1
        return booking


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
    bootstrap_workspace_paths()
    from muscles.asgi.restful import RestApi as AsgiRestApi
    from muscles.asgi.asgi.routers import routes as asgi_routes
    from muscles.wsgi.restful import RestApi as WsgiRestApi
    from muscles.wsgi.wsgi.routers import routes as wsgi_routes

    suffix = uuid.uuid4().hex[:8]
    AsgiRestApi(prefix=f"/api/{suffix}", name=f"api-asgi-{suffix}", title="ASGI API")
    WsgiRestApi(prefix=f"/api/{suffix}", name=f"api-wsgi-{suffix}", title="WSGI API")

    req_docs = SimpleNamespace(path="/docs", method="GET", content_type="text/html")
    req_openapi = SimpleNamespace(path="/openapi.json", method="GET", content_type="application/json")

    asgi_docs, _ = asgi_routes.get_current_route(req_docs)
    asgi_openapi, _ = asgi_routes.get_current_route(req_openapi)
    wsgi_docs, _ = wsgi_routes.get_current_route(req_docs)
    wsgi_openapi, _ = wsgi_routes.get_current_route(req_openapi)
    return {
        "asgi_docs": bool(asgi_docs),
        "asgi_openapi": bool(asgi_openapi),
        "wsgi_docs": bool(wsgi_docs),
        "wsgi_openapi": bool(wsgi_openapi),
    }


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
    from muscles.asgi.asgi.routers import routes as asgi_routes
    from muscles.wsgi.wsgi.routers import routes as wsgi_routes

    req = SimpleNamespace(path="/openapi.json", method="GET", content_type="application/json")
    asgi_route, _ = asgi_routes.get_current_route(req)
    wsgi_route, _ = wsgi_routes.get_current_route(req)
    return {
        "direct_asgi_router": bool(asgi_route),
        "direct_wsgi_router": bool(wsgi_route),
        "fair_contour": True,
        "contour": "direct-no-network",
    }
