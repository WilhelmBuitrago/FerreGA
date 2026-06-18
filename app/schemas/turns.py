from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.types import TurnStatus


class TurnOpened(BaseModel):
    turn_id: UUID
    account_id: UUID
    start_amount: Decimal


class TurnClosed(BaseModel):
    turn_id: UUID
    end_amount: Decimal
    movements_count: int


class ActiveTurn(BaseModel):
    turn_id: UUID
    start_amount: Decimal


class GlobalTurnSummary(BaseModel):
    turn_group_id: UUID
    status: TurnStatus
    opened_at: datetime
    liquidity: float
    incomes: float
    expenses: float
    turn_devengo: float
    turn_cxc: float
    turn_cxp: float


class TurnGroup(BaseModel):
    turn_group_id: UUID
    status: str  # "OPEN" or "CLOSED"
    opened_at: datetime
    closed_at: datetime | None
    account_count: int


class TurnGroupListResponse(BaseModel):
    groups: list[TurnGroup]

