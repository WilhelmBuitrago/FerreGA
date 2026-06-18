from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.engine import Connection

from app.services import movements as movement_service
from app.services import turns as turn_service


class SyncCommandError(ValueError):
    pass


def _handle_command(connection: Connection, command: dict) -> dict:
    command_type = command.get("type")
    payload = dict(command.get("payload") or {})

    if (
        command_type in {"income", "expense", "transfer"}
        and "idempotency_key" not in payload
    ):
        payload["idempotency_key"] = command.get("idempotency_key")

    if command_type == "income":
        return movement_service.add_income(connection, **payload)
    if command_type == "expense":
        return movement_service.add_expense(connection, **payload)
    if command_type == "transfer":
        return movement_service.add_transfer(connection, **payload)
    if command_type == "open_turn":
        return turn_service.open_turn(connection, **payload)
    if command_type == "close_turn":
        return turn_service.close_turn(connection, **payload)
    if command_type == "open_turn_global":
        return turn_service.open_global_turn(connection)
    if command_type == "close_turn_global":
        return turn_service.close_global_turn(connection)

    raise SyncCommandError("Unknown command type")


def process_sync(connection: Connection, *, commands: Iterable[dict]) -> list[dict]:
    results: list[dict] = []
    for command in commands:
        command_id = command.get("id") or command.get("idempotency_key")
        try:
            with connection.begin_nested():
                _handle_command(connection, command)
            results.append(
                {"command_id": command_id, "status": "processed", "error": None}
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "command_id": command_id,
                    "status": "rejected",
                    "error": str(exc),
                }
            )
    return results
