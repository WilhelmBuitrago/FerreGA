from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MessageContext(BaseModel):
    role: str  # "user" o "assistant"
    content: str


class UsageStats(BaseModel):
    minute_requests: int = Field(..., description="Requests in the current minute")
    day_requests: int = Field(..., description="Requests today")
    day_tokens: int = Field(..., description="Tokens used today")
    rpm_limit: int = Field(..., description="Requests per minute limit")
    rpd_limit: int = Field(..., description="Requests per day limit")
    tpd_limit: int = Field(..., description="Tokens per day limit")


class ParseIncomeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language description of income")
    context: list[MessageContext] = Field(default=[], description="Previous conversation turns (optional)")


class ParsedIncome(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., gt=0)
    categoria_codigo: str
    description: str | None = None


class ParsedExpense(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., gt=0)
    categoria_codigo: str
    description: str | None = None


class ParsedTransfer(BaseModel):
    source_account_id: UUID
    target_account_id: UUID
    amount: Decimal = Field(..., gt=0)
    description: str | None = None


class ParsedCreditCreate(BaseModel):
    type: str  # "CREDIT_SALE" or "CREDIT_PURCHASE"
    total_amount: Decimal = Field(..., gt=0)
    due_date: datetime
    description: str | None = None


class ParseIncomeResponse(BaseModel):
    movement: ParsedIncome
    confidence: float = Field(..., ge=0, le=1)
    usage: UsageStats


class ParseExpenseRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language description of expense")
    context: list[MessageContext] = Field(default=[], description="Previous conversation turns (optional)")


class ParseExpenseResponse(BaseModel):
    movement: ParsedExpense
    confidence: float = Field(..., ge=0, le=1)
    usage: UsageStats


class ParseTransferRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language description of transfer")
    context: list[MessageContext] = Field(default=[], description="Previous conversation turns (optional)")


class ParseTransferResponse(BaseModel):
    movement: ParsedTransfer
    confidence: float = Field(..., ge=0, le=1)
    usage: UsageStats


class ParseCreditRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language description of credit payment")
    context: list[MessageContext] = Field(default=[], description="Previous conversation turns (optional)")


class ParseCreditResponse(BaseModel):
    movement: ParsedCreditCreate
    confidence: float = Field(..., ge=0, le=1)
    usage: UsageStats


# === Unified auto-detect schemas ===
from datetime import datetime

from pydantic import BaseModel, Field


class ParseAutoRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language description of any financial movement")
    context: list[MessageContext] = Field(default=[], description="Previous conversation turns (optional)")


class ParseAutoResponse(BaseModel):
    movement_type: Literal["income", "expense", "transfer", "credit_create"]
    # Common fields
    amount: Decimal | None = None  # for income/expense/transfer
    description: str | None = None
    # Income/Expense
    account_id: UUID | None = None
    categoria_codigo: str | None = None
    # Transfer
    source_account_id: UUID | None = None
    target_account_id: UUID | None = None
    # Credit creation
    type: str | None = None  # "CREDIT_SALE" or "CREDIT_PURCHASE"
    total_amount: Decimal | None = None
    due_date: datetime | None = None
    # Meta
    confidence: float = Field(..., ge=0, le=1)
    usage: UsageStats


class AIParseError(BaseModel):
    error: str
    detail: str
    suggestions: list[str] | None = None
