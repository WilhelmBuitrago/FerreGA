from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.types import CreditStatus, CreditType


class CreditCreate(BaseModel):
    type: CreditType
    total_amount: Decimal = Field(..., gt=0)
    due_date: datetime
    description: str | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_past(cls, v: datetime) -> datetime:
        # Compare against current date (ignoring time) to avoid timezone issues with date-only input
        from datetime import date, timezone
        today = datetime.now(timezone.utc).date()
        if v.date() < today:
            raise ValueError("due_date cannot be in the past")
        return v


class CreditUpdate(BaseModel):
    total_amount: Decimal | None = Field(None, gt=0)
    due_date: datetime | None = None
    description: str | None = None
    status: CreditStatus | None = None


class CreditPayment(BaseModel):
    amount: Decimal = Field(..., gt=0)
    account_id: UUID
    description: str | None = None


class CreditResponse(BaseModel):
    id: UUID
    account_id: UUID | None = None
    type: CreditType
    total_amount: Decimal
    paid_amount: Decimal
    due_date: datetime
    status: CreditStatus
    description: str | None
    created_at: datetime
    updated_at: datetime


class CreditSummary(BaseModel):
    cxc_total: Decimal
    cxp_total: Decimal
    devengo_total: Decimal  # suma de ingresos - egresos (desde créditos, no movements)


class TurnSummaryExtended(BaseModel):
    turn_group_id: UUID
    status: str
    opened_at: datetime
    liquidity: Decimal
    incomes: Decimal
    expenses: Decimal
    turn_devengo: Decimal
    turn_cxc: Decimal
    turn_cxp: Decimal
