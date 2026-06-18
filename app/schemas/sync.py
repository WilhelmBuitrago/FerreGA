from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SyncCommand(BaseModel):
    id: UUID | None = None
    type: str
    payload: dict
    timestamp: datetime
    idempotency_key: UUID


class SyncRequest(BaseModel):
    commands: list[SyncCommand]


class SyncCommandResult(BaseModel):
    command_id: UUID | None = None
    status: str
    error: str | None = None


class SyncResponse(BaseModel):
    results: list[SyncCommandResult]
