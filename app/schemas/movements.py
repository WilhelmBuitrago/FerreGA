from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.types import MovementType


class MovementIncomeRequest(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., gt=0)
    description: str | None = None
    categoria_codigo: str
    idempotency_key: UUID


class MovementExpenseRequest(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., gt=0)
    description: str | None = None
    categoria_codigo: str
    idempotency_key: UUID


class MovementTransferRequest(BaseModel):
    source_account_id: UUID
    target_account_id: UUID
    amount: Decimal = Field(..., gt=0)
    description: str | None = None
    idempotency_key: UUID


class MovementAdded(BaseModel):
    movement_id: UUID
    turn_id: UUID
    new_turn_amount: Decimal


class TransferCompleted(BaseModel):
    movement_id: UUID
    source_turn_id: UUID
    target_turn_id: UUID


class MovementUpdateRequest(BaseModel):
    amount: Decimal | None = Field(None, gt=0)
    description: str | None = None


class MovementUpdated(BaseModel):
    movement_id: UUID
    turn_id: UUID


class MovementRecent(BaseModel):
    id: UUID
    type: MovementType
    amount: Decimal
    description: str | None = None
    categoria_codigo: str | None = None
    timestamp: datetime
    is_outgoing: bool
    turn_id: UUID
    turn_group_id: UUID
    account_id: UUID
    account_name: str


class MovementRecentResponse(BaseModel):
    items: list[MovementRecent]
