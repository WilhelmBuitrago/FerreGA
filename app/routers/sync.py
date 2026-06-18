from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.schemas import sync as sync_schemas
from app.services import sync as sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.post("", response_model=sync_schemas.SyncResponse)
def process_sync(
    payload: sync_schemas.SyncRequest, connection: Connection = Depends(get_db)
):
    results = sync_service.process_sync(
        connection, commands=[command.dict() for command in payload.commands]
    )
    return {"results": results}
