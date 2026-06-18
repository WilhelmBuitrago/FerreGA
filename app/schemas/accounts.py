from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.types import MovementType, TurnStatus


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1)
    initial_balance: Decimal | None = Field(None, ge=0)


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    account_amount: Decimal | None = Field(None, ge=0)


class AccountSummary(BaseModel):
    id: UUID
    name: str
    turn_amount: Decimal
    account_amount: Decimal
    difference: Decimal


class AccountCreated(BaseModel):
    id: UUID
    name: str


class Movement(BaseModel):
    id: UUID
    type: MovementType
    amount: Decimal
    description: str | None = None
    timestamp: datetime


class TurnWithMovements(BaseModel):
    id: UUID
    start_amount: Decimal
    end_amount: Decimal | None = None
    status: TurnStatus
    created_at: datetime
    closed_at: datetime | None = None
    movements: list[Movement]


class AccountDetail(BaseModel):
    id: UUID
    name: str
    liquidity: Decimal
    incomes: Decimal
    expenses: Decimal
    history: list[TurnWithMovements]
