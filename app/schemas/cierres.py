from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.types import EstadoCierre


class CierreCreate(BaseModel):
    turno_id: str = Field(..., min_length=1)
    monto_cierre: Decimal = Field(..., gt=0)
    notas: str | None = None

    @field_validator("turno_id")
    @classmethod
    def turno_id_alias_to_usuario_id(cls, v: str) -> str:
        return v.strip()

    @property
    def usuario_id(self) -> str:
        """Map turno_id to DB column usuario_id."""
        return self.turno_id

    @property
    def balance_real(self) -> Decimal:
        """Map monto_cierre to DB column balance_real."""
        return self.monto_cierre


class CierreOut(BaseModel):
    id: UUID
    fecha: datetime
    usuario_id: str
    balance_esperado: Decimal
    balance_real: Decimal
    diferencia: Decimal
    estado: EstadoCierre
    edit_lock: bool
    notas: str | None = None


class CierreLockOut(BaseModel):
    id: UUID
    edit_lock: bool
    estado: EstadoCierre