from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Booking:
    booking_id: int
    title: str


class BookingApp:
    """Golden path benchmark app with one use case reused across transports."""

    def __init__(self) -> None:
        self._next_id = 1

    def create_booking(self, title: str) -> Booking:
        booking = Booking(booking_id=self._next_id, title=title)
        self._next_id += 1
        return booking

    # API-like call shape (JsonResponse/OpenAPI scope)
    def api_create_booking(self, payload: dict) -> dict:
        booking = self.create_booking(payload["title"])
        return {"booking_id": booking.booking_id, "title": booking.title}

    # CLI-like call shape (nested command args scope)
    def cli_bookings_create(self, title: str) -> str:
        booking = self.create_booking(title)
        return f"created:{booking.booking_id}:{booking.title}"

    # SQL-like call shape (map_model + insert path scope)
    def sql_insert_booking(self, title: str) -> int:
        booking = self.create_booking(title)
        return booking.booking_id

    # Contract-like call for adapters (MCP/JSON-RPC scope)
    def action_call(self, action_name: str, args: dict) -> dict:
        if action_name != "bookings.create":
            raise KeyError(action_name)
        return self.api_create_booking(args)
