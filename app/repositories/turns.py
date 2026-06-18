from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from app.core.types import TurnStatus
from app.models.tables import turns


def create_turn(
    connection: Connection,
    *,
    account_id: UUID,
    start_amount: Decimal,
    turn_group_id: UUID,
) -> dict:
    result = connection.execute(
        insert(turns)
        .values(
            id=uuid4(),
            account_id=account_id,
            start_amount=start_amount,
            status=TurnStatus.OPEN,
            turn_group_id=turn_group_id,
        )
        .returning(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.status,
            turns.c.created_at,
        )
    )
    return result.mappings().one()


def create_closed_turn(
    connection: Connection,
    *,
    account_id: UUID,
    start_amount: Decimal,
    end_amount: Decimal,
    turn_group_id: UUID,
) -> dict:
    result = connection.execute(
        insert(turns)
        .values(
            id=uuid4(),
            account_id=account_id,
            start_amount=start_amount,
            end_amount=end_amount,
            status=TurnStatus.CLOSED,
            closed_at=datetime.utcnow(),
            turn_group_id=turn_group_id,
        )
        .returning(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.end_amount,
            turns.c.status,
            turns.c.created_at,
            turns.c.closed_at,
        )
    )
    return result.mappings().one()


def get_turn(connection: Connection, *, turn_id: UUID) -> dict | None:
    result = connection.execute(
        select(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.end_amount,
            turns.c.status,
            turns.c.created_at,
            turns.c.closed_at,
        ).where(turns.c.id == turn_id)
    )
    return result.mappings().one_or_none()


def get_active_turn(connection: Connection, *, account_id: UUID) -> dict | None:
    result = connection.execute(
        select(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.end_amount,
            turns.c.status,
            turns.c.created_at,
            turns.c.closed_at,
        ).where(
            turns.c.account_id == account_id,
            turns.c.status == TurnStatus.OPEN,
        )
    )
    return result.mappings().one_or_none()


def list_turns_for_account(connection: Connection, *, account_id: UUID) -> list[dict]:
    result = connection.execute(
        select(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.end_amount,
            turns.c.status,
            turns.c.created_at,
            turns.c.closed_at,
        )
        .where(turns.c.account_id == account_id)
        .order_by(turns.c.created_at.desc())
    )
    return list(result.mappings().all())


def list_turns_by_group(
    connection: Connection,
    *,
    turn_group_id: UUID,
    status: TurnStatus | None = None,
) -> list[dict]:
    query = select(
        turns.c.id,
        turns.c.turn_group_id,
        turns.c.account_id,
        turns.c.start_amount,
        turns.c.end_amount,
        turns.c.status,
        turns.c.created_at,
        turns.c.closed_at,
    ).where(turns.c.turn_group_id == turn_group_id)
    if status is not None:
        query = query.where(turns.c.status == status)
    result = connection.execute(query.order_by(turns.c.created_at.asc()))
    return list(result.mappings().all())


def get_active_group_id(connection: Connection) -> UUID | None:
    result = connection.execute(
        select(turns.c.turn_group_id)
        .where(turns.c.status == TurnStatus.OPEN)
        .order_by(turns.c.created_at.desc())
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


def get_latest_closed_group_id(connection: Connection) -> UUID | None:
    result = connection.execute(
        select(turns.c.turn_group_id)
        .where(turns.c.status == TurnStatus.CLOSED)
        .order_by(turns.c.closed_at.desc())
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


def close_turn(
    connection: Connection,
    *,
    turn_id: UUID,
    end_amount: Decimal,
) -> dict | None:
    result = connection.execute(
        update(turns)
        .where(turns.c.id == turn_id)
        .values(
            end_amount=end_amount,
            status=TurnStatus.CLOSED,
            closed_at=datetime.utcnow(),
        )
        .returning(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.end_amount,
            turns.c.status,
            turns.c.created_at,
            turns.c.closed_at,
        )
    )
    return result.mappings().one_or_none()


def update_closed_turn_amount(
    connection: Connection,
    *,
    turn_id: UUID,
    end_amount: Decimal,
) -> dict | None:
    result = connection.execute(
        update(turns)
        .where(turns.c.id == turn_id)
        .values(
            end_amount=end_amount,
            closed_at=datetime.utcnow(),
        )
        .returning(
            turns.c.id,
            turns.c.turn_group_id,
            turns.c.account_id,
            turns.c.start_amount,
            turns.c.end_amount,
            turns.c.status,
            turns.c.created_at,
            turns.c.closed_at,
        )
    )
    return result.mappings().one_or_none()
