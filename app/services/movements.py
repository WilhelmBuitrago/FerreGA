from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.engine import Connection

from app.core.types import MovementType
from app.repositories import idempotency as idempotency_repo
from app.repositories import movements as movement_repo
from app.repositories import turns as turns_repo

logger = logging.getLogger(__name__)


class MovementError(ValueError):
    pass


class MovementNotFoundError(ValueError):
    pass


def _calculate_turn_amount(connection: Connection, *, turn: dict) -> Decimal:
    sums = movement_repo.get_movement_sums(connection, turn_id=turn["id"])
    return (
        Decimal(turn["start_amount"])
        + sums["income"]
        - sums["expense"]
        + (sums["transfer_in"] - sums["transfer_out"])
    )


def add_income(
    connection: Connection,
    *,
    account_id: UUID,
    amount: Decimal,
    description: str | None,
    categoria_codigo: str,
    idempotency_key: UUID,
) -> dict:
    existing = idempotency_repo.get_command_log(
        connection, idempotency_key=idempotency_key
    )
    if existing:
        return existing["response"]

    turn = turns_repo.get_active_turn(connection, account_id=account_id)
    if turn is None:
        raise MovementError("No active turn")
    if amount <= 0:
        raise MovementError("Amount must be positive")

    movement = movement_repo.create_movement(
        connection,
        turn_id=turn["id"],
        movement_type=MovementType.INGRESO,
        amount=amount,
        description=description,
        category_code=categoria_codigo,
    )
    new_turn_amount = _calculate_turn_amount(connection, turn=turn)
    service_response = {
        "movement_id": movement["id"],
        "turn_id": movement["turn_id"],
        "new_turn_amount": new_turn_amount,
    }
    log_response = {
        "movement_id": str(movement["id"]),
        "turn_id": str(movement["turn_id"]),
        "new_turn_amount": float(new_turn_amount),
    }
    idempotency_repo.create_command_log(
        connection,
        idempotency_key=idempotency_key,
        command_type="income",
        response=log_response,
    )
    return service_response


def add_expense(
    connection: Connection,
    *,
    account_id: UUID,
    amount: Decimal,
    description: str | None,
    categoria_codigo: str,
    idempotency_key: UUID,
) -> dict:
    existing = idempotency_repo.get_command_log(
        connection, idempotency_key=idempotency_key
    )
    if existing:
        return existing["response"]

    turn = turns_repo.get_active_turn(connection, account_id=account_id)
    if turn is None:
        raise MovementError("No active turn")
    if amount <= 0:
        raise MovementError("Amount must be positive")

    movement = movement_repo.create_movement(
        connection,
        turn_id=turn["id"],
        movement_type=MovementType.EGRESO,
        amount=amount,
        description=description,
        category_code=categoria_codigo,
    )
    new_turn_amount = _calculate_turn_amount(connection, turn=turn)
    service_response = {
        "movement_id": movement["id"],
        "turn_id": movement["turn_id"],
        "new_turn_amount": new_turn_amount,
    }
    log_response = {
        "movement_id": str(movement["id"]),
        "turn_id": str(movement["turn_id"]),
        "new_turn_amount": float(new_turn_amount),
    }
    idempotency_repo.create_command_log(
        connection,
        idempotency_key=idempotency_key,
        command_type="expense",
        response=log_response,
    )
    return service_response


def add_transfer(
    connection: Connection,
    *,
    source_account_id: UUID,
    target_account_id: UUID,
    amount: Decimal,
    description: str | None,
    idempotency_key: UUID,
) -> dict:
    existing = idempotency_repo.get_command_log(
        connection, idempotency_key=idempotency_key
    )
    if existing:
        return existing["response"]

    if source_account_id == target_account_id:
        raise MovementError("Source and target must differ")
    if amount <= 0:
        raise MovementError("Amount must be positive")

    source_turn = turns_repo.get_active_turn(connection, account_id=source_account_id)
    if source_turn is None:
        raise MovementError("No active turn for source account")
    target_turn = turns_repo.get_active_turn(connection, account_id=target_account_id)
    if target_turn is None:
        raise MovementError("No active turn for target account")

    outgoing = movement_repo.create_movement(
        connection,
        turn_id=source_turn["id"],
        movement_type=MovementType.TRANSFERENCIA,
        amount=amount,
        description=description,
        is_outgoing=True,
    )
    movement_repo.create_movement(
        connection,
        turn_id=target_turn["id"],
        movement_type=MovementType.TRANSFERENCIA,
        amount=amount,
        description=description,
        is_outgoing=False,
    )

    service_response = {
        "movement_id": outgoing["id"],
        "source_turn_id": source_turn["id"],
        "target_turn_id": target_turn["id"],
    }

    log_response = {
        "movement_id": str(outgoing["id"]),
        "source_turn_id": str(source_turn["id"]),
        "target_turn_id": str(target_turn["id"]),
    }
    idempotency_repo.create_command_log(
        connection,
        idempotency_key=idempotency_key,
        command_type="transfer",
        response=log_response,
    )
    return service_response


def update_movement(
    connection: Connection,
    *,
    movement_id: UUID,
    amount: Decimal | None,
    description: str | None,
) -> dict:
    movement = movement_repo.get_movement(connection, movement_id=movement_id)
    if movement is None or not movement.get("is_active", True):
        raise MovementNotFoundError("Movement not found")
    if movement["type"] == MovementType.TRANSFERENCIA:
        raise MovementError("Transfer adjustments are not supported yet")
    updated = movement_repo.update_movement(
        connection,
        movement_id=movement_id,
        amount=amount,
        description=description,
    )
    if updated is None:
        raise MovementNotFoundError("Movement not found")
    return {
        "movement_id": updated["id"],
        "turn_id": updated["turn_id"],
    }


def delete_movement(connection: Connection, *, movement_id: UUID) -> None:
    movement = movement_repo.get_movement(connection, movement_id=movement_id)
    if movement is None or not movement.get("is_active", True):
        raise MovementNotFoundError("Movement not found")
    if movement["type"] == MovementType.TRANSFERENCIA:
        raise MovementError("Transfer deletions are not supported yet")
    deleted = movement_repo.soft_delete_movement(connection, movement_id=movement_id)
    if not deleted:
        raise MovementNotFoundError("Movement not found")


def list_recent_movements(
    connection: Connection,
    *,
    limit: int,
    skip: int = 0,
    turn_group_id: UUID | None = None,
    account_id: UUID | None = None,
    movement_type: MovementType | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    description_regex: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    return movement_repo.list_recent_movements(
        connection,
        limit=limit,
        skip=skip,
        turn_group_id=turn_group_id,
        account_id=account_id,
        movement_type=movement_type,
        amount_min=amount_min,
        amount_max=amount_max,
        description_regex=description_regex,
        start_date=start_date,
        end_date=end_date,
    )
