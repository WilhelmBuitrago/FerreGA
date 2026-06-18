from __future__ import annotations

import os
import time
import uuid
from enum import Enum


class EstadoCierre(str, Enum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class TurnStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class MovementType(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"
    TRANSFERENCIA = "TRANSFERENCIA"


class CreditType(str, Enum):
    CREDIT_SALE = "CREDIT_SALE"      # Venta a crédito (CxC)
    CREDIT_PURCHASE = "CREDIT_PURCHASE"  # Compra a crédito (CxP)


class CreditStatus(str, Enum):
    PENDIENTE = "PENDIENTE"
    PARCIAL = "PARCIAL"
    PAGADO = "PAGADO"


class CategoriaTipo(str, Enum):
    INGRESO = "INGRESO"
    GASTO = "GASTO"
    PASIVO = "PASIVO"
    ACTIVO = "ACTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"


class TipoTransaccion(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"
    TRANSFERENCIA = "TRANSFERENCIA"


class EstadoTransaccion(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (time-ordered) without external deps."""
    unix_ms = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big")
    rand_b = (rand_b & 0x3FFFFFFFFFFFFFFF) | 0x8000000000000000
    uuid_int = (unix_ms << 80) | (0x7 << 76) | (rand_a << 64) | rand_b
    return uuid.UUID(int=uuid_int)
