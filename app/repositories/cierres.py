from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.engine import Connection

from app.core.types import EstadoCierre
from app.models.tables import cierres


def create_cierre(
    connection: Connection,
    *,
    usuario_id: str,
    balance_esperado: Decimal,
    balance_real: Decimal,
    diferencia: Decimal,
    notas: str | None,
) -> dict:
    from uuid import uuid4
    result = connection.execute(
        insert(cierres)
        .values(
            id=uuid4(),
            usuario_id=usuario_id,
            balance_esperado=balance_esperado,
            balance_real=balance_real,
            diferencia=diferencia,
            notas=notas,
            estado=EstadoCierre.CERRADO,
            edit_lock=True,
        )
        .returning(
            cierres.c.id,
            cierres.c.fecha,
            cierres.c.usuario_id,
            cierres.c.balance_esperado,
            cierres.c.balance_real,
            cierres.c.diferencia,
            cierres.c.estado,
            cierres.c.edit_lock,
            cierres.c.notas,
        )
    )
    return result.mappings().one()


def get_cierre_by_usuario_dia(
    connection: Connection,
    *,
    usuario_id: str,
    fecha: date,
) -> dict | None:
    result = connection.execute(
        select(
            cierres.c.id,
            cierres.c.fecha,
            cierres.c.usuario_id,
            cierres.c.balance_esperado,
            cierres.c.balance_real,
            cierres.c.diferencia,
            cierres.c.estado,
            cierres.c.edit_lock,
            cierres.c.notas,
        )
        .where(
            cierres.c.usuario_id == usuario_id,
            func.date(cierres.c.fecha) == fecha,
            cierres.c.is_active.is_(True),
        )
        .order_by(cierres.c.fecha.desc())
        .limit(1)
    )
    return result.mappings().one_or_none()


def get_cierre(connection: Connection, *, cierre_id: UUID) -> dict | None:
    result = connection.execute(
        select(
            cierres.c.id,
            cierres.c.fecha,
            cierres.c.usuario_id,
            cierres.c.balance_esperado,
            cierres.c.balance_real,
            cierres.c.diferencia,
            cierres.c.estado,
            cierres.c.edit_lock,
            cierres.c.notas,
        ).where(cierres.c.id == cierre_id, cierres.c.is_active.is_(True))
    )
    return result.mappings().one_or_none()


def list_cierres(connection: Connection) -> list[dict]:
    result = connection.execute(
        select(
            cierres.c.id,
            cierres.c.fecha,
            cierres.c.usuario_id,
            cierres.c.balance_esperado,
            cierres.c.balance_real,
            cierres.c.diferencia,
            cierres.c.estado,
            cierres.c.edit_lock,
            cierres.c.notas,
        ).where(cierres.c.is_active.is_(True))
    )
    return list(result.mappings().all())


def lock_cierre(connection: Connection, *, cierre_id: UUID) -> dict | None:
    result = connection.execute(
        cierres.update()
        .where(cierres.c.id == cierre_id)
        .values(edit_lock=True)
        .returning(
            cierres.c.id,
            cierres.c.edit_lock,
        )
    )
    return result.mappings().one_or_none()
