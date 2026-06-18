from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from app.core.types import EstadoCierre, EstadoTransaccion, TipoTransaccion
from app.models.tables import transacciones
from app.repositories import cierres as cierre_repo


class CierreDuplicadoError(ValueError):
    error_code = "duplicate"


class CierreLockedError(ValueError):
    error_code = "locked"


class CierreValidationError(ValueError):
    error_code = "validation"


def calcular_balance_esperado(connection: Connection, *, usuario_id: str) -> Decimal:
    ingreso_sum = func.coalesce(func.sum(transacciones.c.monto), 0)
    result = connection.execute(
        select(
            ingreso_sum
            .filter(transacciones.c.tipo == TipoTransaccion.INGRESO)
            .label("ingresos"),
            ingreso_sum
            .filter(transacciones.c.tipo == TipoTransaccion.EGRESO)
            .label("egresos"),
        ).where(
            transacciones.c.estado == EstadoTransaccion.CONFIRMADO,
            transacciones.c.cuenta_codigo == usuario_id,
        )
    )
    row = result.first()
    if row is None:
        return Decimal("0")
    ingresos = row.ingresos or Decimal("0")
    egresos = row.egresos or Decimal("0")
    return Decimal(ingresos) - Decimal(egresos)


def registrar_cierre(
    connection: Connection,
    *,
    turno_id: str,
    monto_cierre: Decimal,
    notas: str | None,
) -> tuple[dict, bool]:
    usuario_id = turno_id
    balance_real = monto_cierre

    balance_esperado = calcular_balance_esperado(connection, usuario_id=usuario_id)
    if balance_real <= 0:
        raise CierreValidationError("Monto de cierre debe ser positivo")

    if balance_esperado == 0:
        diferencia_ratio = Decimal("0") if balance_real == 0 else Decimal("1")
    else:
        diferencia_ratio = (balance_real - balance_esperado).copy_abs() / balance_esperado

    if diferencia_ratio > Decimal("0.05") and not notas:
        raise CierreValidationError("Notas son obligatorias cuando hay desviación >5%")

    existing = cierre_repo.get_cierre_by_usuario_dia(
        connection,
        usuario_id=usuario_id,
        fecha=datetime.utcnow().date(),
    )
    if existing:
        if (
            existing["balance_real"] == balance_real
            and existing["balance_esperado"] == balance_esperado
            and (existing.get("notas") or None) == (notas or None)
        ):
            return existing, False
        raise CierreDuplicadoError("Cierre duplicado")

    diferencia = balance_real - balance_esperado
    return (
        cierre_repo.create_cierre(
            connection,
            usuario_id=usuario_id,
            balance_esperado=balance_esperado,
            balance_real=balance_real,
            diferencia=diferencia,
            notas=notas,
        ),
        True,
    )


def get_cierre(connection: Connection, *, cierre_id: UUID) -> dict:
    cierre = cierre_repo.get_cierre(connection, cierre_id=cierre_id)
    if cierre is None:
        raise CierreLockedError("Cierre no encontrado")
    return cierre


def list_cierres(connection: Connection) -> list[dict]:
    return cierre_repo.list_cierres(connection)