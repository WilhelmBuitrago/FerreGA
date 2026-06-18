from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.core.security import require_admin
from app.core.types import MovementType
from app.schemas import movements as movement_schemas
from app.services import movements as movement_service

router = APIRouter(prefix="/movements", tags=["movements"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.post(
    "/income",
    response_model=movement_schemas.MovementAdded,
    status_code=status.HTTP_201_CREATED,
)
def add_income(
    payload: movement_schemas.MovementIncomeRequest,
    connection: Connection = Depends(get_db),
):
    try:
        return movement_service.add_income(
            connection,
            account_id=payload.account_id,
            amount=payload.amount,
            description=payload.description,
            categoria_codigo=payload.categoria_codigo,
            idempotency_key=payload.idempotency_key,
        )
    except movement_service.MovementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/expense",
    response_model=movement_schemas.MovementAdded,
    status_code=status.HTTP_201_CREATED,
)
def add_expense(
    payload: movement_schemas.MovementExpenseRequest,
    connection: Connection = Depends(get_db),
):
    try:
        return movement_service.add_expense(
            connection,
            account_id=payload.account_id,
            amount=payload.amount,
            description=payload.description,
            categoria_codigo=payload.categoria_codigo,
            idempotency_key=payload.idempotency_key,
        )
    except movement_service.MovementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/transfer",
    response_model=movement_schemas.TransferCompleted,
    status_code=status.HTTP_201_CREATED,
)
def add_transfer(
    payload: movement_schemas.MovementTransferRequest,
    connection: Connection = Depends(get_db),
):
    try:
        return movement_service.add_transfer(
            connection,
            source_account_id=payload.source_account_id,
            target_account_id=payload.target_account_id,
            amount=payload.amount,
            description=payload.description,
            idempotency_key=payload.idempotency_key,
        )
    except movement_service.MovementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch(
    "/{movement_id}",
    response_model=movement_schemas.MovementUpdated,
)
def update_movement(
    movement_id: UUID,
    payload: movement_schemas.MovementUpdateRequest,
    connection: Connection = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        return movement_service.update_movement(
            connection,
            movement_id=movement_id,
            amount=payload.amount,
            description=payload.description,
        )
    except movement_service.MovementNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except movement_service.MovementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: UUID,
    connection: Connection = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        movement_service.delete_movement(connection, movement_id=movement_id)
    except movement_service.MovementNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except movement_service.MovementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return None


@router.get("/recent", response_model=movement_schemas.MovementRecentResponse)
def list_recent_movements(
    limit: int = 50,
    skip: int = 0,
    turn_group_id: UUID | None = None,
    account_id: UUID | None = None,
    movement_type: MovementType | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    description_regex: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    connection: Connection = Depends(get_db),
):
    # Convertir fechas ISO a datetime si se proporcionan
    from datetime import datetime
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato start_date inválido, use ISO 8601")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato end_date inválido, use ISO 8601")
    items = movement_service.list_recent_movements(
        connection,
        limit=min(max(limit, 1), 100),
        skip=min(max(skip, 0), 1000),
        turn_group_id=turn_group_id,
        account_id=account_id,
        movement_type=movement_type,
        amount_min=None if amount_min is None else Decimal(str(amount_min)),
        amount_max=None if amount_max is None else Decimal(str(amount_max)),
        description_regex=description_regex,
        start_date=start_dt,
        end_date=end_dt,
    )
    return {"items": items}
