from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.core.security import get_current_user, require_admin
from app.schemas import credits as credit_schemas
from app.services import credits as credit_service

router = APIRouter(prefix="/credits", tags=["credits"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.post("", response_model=credit_schemas.CreditResponse, status_code=status.HTTP_201_CREATED)
def create_credit(
    payload: credit_schemas.CreditCreate, connection: Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user),
):
    try:
        return credit_service.create_credit(
            connection,
            type=payload.type,
            total_amount=payload.total_amount,
            due_date=payload.due_date,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[credit_schemas.CreditResponse])
def list_credits(
    account_id: UUID | None = None,
    status: str | None = None,
    connection: Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user),
):
    return credit_service.list_credits(connection, account_id=account_id, status=status)


@router.get("/summary", response_model=credit_schemas.CreditSummary)
def get_credit_summary(
    account_id: UUID | None = None,
    connection: Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user),
):
    return credit_service.get_credit_summary(connection, account_id=account_id)


@router.post("/{credit_id}/pay", response_model=credit_schemas.CreditResponse)
def pay_credit(
    credit_id: UUID,
    payload: credit_schemas.CreditPayment,
    connection: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        result = credit_service.pay_credit(
            connection,
            credit_id=credit_id,
            amount=payload.amount,
            account_id=payload.account_id,
            description=payload.description,
        )
        return result["credit"]
    except credit_service.CreditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{credit_id}", response_model=credit_schemas.CreditResponse)
def update_credit(
    credit_id: UUID,
    payload: credit_schemas.CreditUpdate,
    connection: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return credit_service.update_credit(
            connection,
            credit_id=credit_id,
            total_amount=payload.total_amount,
            due_date=payload.due_date,
            description=payload.description,
        )
    except credit_service.CreditError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
