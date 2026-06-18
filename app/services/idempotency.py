from __future__ import annotations

from uuid import UUID

from sqlalchemy.engine import Connection

from app.repositories import idempotency as idempotency_repo


def get_existing_response(
    connection: Connection, *, idempotency_key: UUID
) -> dict | None:
    record = idempotency_repo.get_command_log(
        connection, idempotency_key=idempotency_key
    )
    if record:
        return record["response"]
    return None
