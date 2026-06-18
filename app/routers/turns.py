from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.schemas import turns as turn_schemas
from app.schemas import turns_payloads as payload_schemas
from app.services import turns as turn_service

router = APIRouter(prefix="/turns", tags=["turns"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.post(
    "/open", response_model=turn_schemas.TurnOpened, status_code=status.HTTP_201_CREATED
)
def open_turn(
    payload: payload_schemas.TurnOpenRequest, connection: Connection = Depends(get_db)
):
    try:
        result = turn_service.open_turn(connection, account_id=payload.account_id)
        return {
            "turn_id": result["id"],
            "account_id": result["account_id"],
            "start_amount": result["start_amount"],
        }
    except turn_service.ActiveTurnExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{turn_id}/close", response_model=turn_schemas.TurnClosed)
def close_turn(turn_id: UUID, connection: Connection = Depends(get_db)):
    try:
        return turn_service.close_turn(connection, turn_id=turn_id)
    except turn_service.TurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/active", response_model=turn_schemas.ActiveTurn)
def get_active_turn(account_id: UUID, connection: Connection = Depends(get_db)):
    try:
        return turn_service.get_active_turn(connection, account_id=account_id)
    except turn_service.TurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/active-global", response_model=turn_schemas.GlobalTurnSummary)
def get_active_global_turn(
    account_id: UUID | None = None, connection: Connection = Depends(get_db)
):
    try:
        return turn_service.get_global_turn_summary(connection, account_id=account_id)
    except turn_service.GlobalTurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/open-global",
    response_model=turn_schemas.GlobalTurnSummary,
    status_code=status.HTTP_201_CREATED,
)
def open_global_turn(connection: Connection = Depends(get_db)):
    try:
        result = turn_service.open_global_turn(connection)
        return turn_service.get_global_turn_summary(connection)
    except turn_service.ActiveTurnExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/close-global", response_model=turn_schemas.GlobalTurnSummary)
def close_global_turn(connection: Connection = Depends(get_db)):
    try:
        turn_service.close_global_turn(connection)
        return turn_service.get_global_turn_summary(connection)
    except turn_service.GlobalTurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/groups", response_model=turn_schemas.TurnGroupListResponse)
def list_turn_groups(connection: Connection = Depends(get_db)):
    try:
        groups = turn_service.list_turn_groups(connection)
        return {"groups": groups}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/summary/historical", response_model=turn_schemas.GlobalTurnSummary)
def get_historical_summary(connection: Connection = Depends(get_db)):
    try:
        return turn_service.get_historical_summary(connection)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/group/{turn_group_id}/summary", response_model=turn_schemas.GlobalTurnSummary)
def get_group_summary(
    turn_group_id: UUID,
    account_id: UUID | None = None,
    connection: Connection = Depends(get_db)
):
    try:
        return turn_service.get_global_turn_summary(
            connection,
            account_id=account_id,
            turn_group_id=turn_group_id
        )
    except turn_service.GlobalTurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

