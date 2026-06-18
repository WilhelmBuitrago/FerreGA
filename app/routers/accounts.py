from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.core.security import get_current_user, require_admin
from app.schemas import accounts as schemas
from app.services import accounts as account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.get("", response_model=list[schemas.AccountSummary])
def list_accounts(
    include_inactive: bool = False,
    connection: Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user),
):
    if include_inactive and (user is None or user.get("role") != "admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    return account_service.list_accounts(connection, include_inactive=include_inactive)


@router.post(
    "", response_model=schemas.AccountCreated, status_code=status.HTTP_201_CREATED
)
def create_account(
    payload: schemas.AccountCreate, connection: Connection = Depends(get_db)
):
    try:
        return account_service.create_account(
            connection, name=payload.name, initial_balance=payload.initial_balance
        )
    except account_service.AccountAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{account_id}", response_model=schemas.AccountSummary)
def update_account(
    account_id: UUID,
    payload: schemas.AccountUpdate,
    connection: Connection = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        return account_service.update_account(
            connection,
            account_id=account_id,
            name=payload.name,
            account_amount=payload.account_amount,
        )
    except account_service.AccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except account_service.AccountAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except account_service.AccountUpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{account_id}", response_model=schemas.AccountDetail)
def get_account(
    account_id: UUID,
    include_inactive: bool = False,
    connection: Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user),
):
    try:
        if include_inactive and (user is None or user.get("role") != "admin"):
            raise HTTPException(status_code=403, detail="Admin required")
        return account_service.get_account_detail(
            connection, account_id=account_id, include_inactive=include_inactive
        )
    except account_service.AccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: UUID,
    force: bool = False,
    hard_delete: bool = False,
    connection: Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user),
):
    is_admin = user is not None and user.get("role") == "admin"
    if (force or hard_delete) and not is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        account_service.delete_account(
            connection,
            account_id=account_id,
            allow_nonzero=is_admin and force,
            hard_delete=is_admin and hard_delete,
        )
    except account_service.AccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except account_service.AccountDeletionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return None
