from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.engine import Connection

from app.models.tables import command_log


def get_command_log(connection: Connection, *, idempotency_key: UUID) -> dict | None:
    result = connection.execute(
        select(
            command_log.c.id,
            command_log.c.idempotency_key,
            command_log.c.command_type,
            command_log.c.response,
            command_log.c.created_at,
        ).where(command_log.c.idempotency_key == idempotency_key)
    )
    row = result.mappings().one_or_none()
    if row is not None:
        row_dict = dict(row)
        # response está almacenado como TEXT (JSON string). Convertir a dict si es string.
        if isinstance(row_dict.get("response"), str):
            row_dict["response"] = json.loads(row_dict["response"])
        return row_dict
    return None


def create_command_log(
    connection: Connection,
    *,
    idempotency_key: UUID,
    command_type: str,
    response: dict,
) -> dict:
    from uuid import uuid4
    # Convertir el dict a JSON string para guardar en SQLite TEXT
    response_json = json.dumps(response)
    result = connection.execute(
        insert(command_log)
        .values(
            id=uuid4(),
            idempotency_key=idempotency_key,
            command_type=command_type,
            response=response_json,
        )
        .returning(
            command_log.c.id,
            command_log.c.idempotency_key,
            command_log.c.command_type,
            command_log.c.response,
            command_log.c.created_at,
        )
    )
    row = result.mappings().one()
    row_dict = dict(row)
    # response viene como string desde DB, convertirlo a dict para API
    if isinstance(row_dict.get("response"), str):
        row_dict["response"] = json.loads(row_dict["response"])
    return row_dict
