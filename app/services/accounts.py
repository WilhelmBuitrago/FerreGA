from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.engine import Connection

from app.core.types import TurnStatus, MovementType
from app.repositories import accounts as accounts_repo
from app.repositories import movements as movement_repo
from app.repositories import turns as turns_repo


class AccountNotFoundError(ValueError):
    pass


class AccountAlreadyExistsError(ValueError):
    pass


class AccountDeletionError(ValueError):
    pass


class AccountUpdateError(ValueError):
    pass


def _calculate_turn_amount(connection: Connection, *, turn: dict) -> Decimal:
    sums = movement_repo.get_movement_sums(connection, turn_id=turn["id"])
    return (
        Decimal(turn["start_amount"])
        + sums["income"]
        - sums["expense"]
        + (sums["transfer_in"] - sums["transfer_out"])
    )


def _get_latest_closed_turn_amount(
    connection: Connection, *, account_id: UUID
) -> Decimal:
    turns = turns_repo.list_turns_for_account(connection, account_id=account_id)
    closed = [
        turn
        for turn in turns
        if turn["status"] == TurnStatus.CLOSED and turn["end_amount"] is not None
    ]
    if not closed:
        return Decimal("0")
    latest = max(closed, key=lambda row: row["closed_at"] or row["created_at"])
    return Decimal(latest["end_amount"] or 0)


def _build_summary(connection: Connection, *, account_id: UUID) -> dict:
    account = accounts_repo.get_account(
        connection, account_id=account_id, include_inactive=True
    )
    if account is None:
        raise AccountNotFoundError("Account not found")
    active_turn = turns_repo.get_active_turn(connection, account_id=account_id)
    if active_turn:
        turn_amount = _calculate_turn_amount(connection, turn=active_turn)
    else:
        turn_amount = Decimal("0")
    # account_amount ya está actualizado en tiempo real en la tabla
    account_amount = Decimal(str(account.get("account_amount") or 0))
    return {
        "id": account["id"],
        "name": account["name"],
        "turn_amount": turn_amount,
        "account_amount": account_amount,
        "difference": account_amount - turn_amount,
        "categoria": "ACTIVO",  # Todas las cuentas son activos
    }


def list_accounts(
    connection: Connection, *, include_inactive: bool = False
) -> list[dict]:
    accounts = accounts_repo.list_accounts(
        connection, include_inactive=include_inactive
    )
    results: list[dict] = []
    for account in accounts:
        if not account.get("is_active", True) and not include_inactive:
            continue
        active_turn = turns_repo.get_active_turn(connection, account_id=account["id"])
        if active_turn:
            turn_amount = _calculate_turn_amount(connection, turn=active_turn)
        else:
            turn_amount = Decimal("0")
        # account_amount ya está actualizado en tiempo real en la tabla
        account_amount = Decimal(str(account.get("account_amount") or 0))
        results.append(
            {
                "id": account["id"],
                "name": account["name"],
                "turn_amount": turn_amount,
                "account_amount": account_amount,
                "difference": account_amount - turn_amount,
                "categoria": "ACTIVO",
            }
        )
    return results


def get_account_detail(
    connection: Connection, *, account_id: UUID, include_inactive: bool = False
) -> dict:
    account = accounts_repo.get_account(
        connection, account_id=account_id, include_inactive=include_inactive
    )
    if account is None:
        raise AccountNotFoundError("Account not found")

    turns = turns_repo.list_turns_for_account(connection, account_id=account_id)
    history: list[dict] = []
    active_turn = None
    active_turn_incomes = Decimal("0")
    active_turn_expenses = Decimal("0")

    for turn in turns:
        movements = movement_repo.list_movements_by_turn(connection, turn_id=turn["id"])
        # Calcular ingresos y egresos del turno (para el turno activo)
        turn_incomes = Decimal("0")
        turn_expenses = Decimal("0")
        for movement in movements:
            if movement["type"] == MovementType.INGRESO:
                turn_incomes += Decimal(movement["amount"])
            elif movement["type"] == MovementType.EGRESO:
                turn_expenses += Decimal(movement["amount"])
        history.append(
            {
                "id": turn["id"],
                "start_amount": turn["start_amount"],
                "end_amount": turn["end_amount"],
                "status": turn["status"],
                "created_at": turn["created_at"],
                "closed_at": turn["closed_at"],
                "movements": [
                    {
                        "id": movement["id"],
                        "type": movement["type"],
                        "amount": movement["amount"],
                        "description": movement["description"],
                        "categoria_codigo": movement.get("categoria_codigo"),
                        "timestamp": movement["timestamp"],
                    }
                    for movement in movements
                ],
            }
        )
        if turn["status"] == TurnStatus.OPEN:
            active_turn = turn
            active_turn_incomes = turn_incomes
            active_turn_expenses = turn_expenses

    if active_turn:
        turn_amount = _calculate_turn_amount(connection, turn=active_turn)
    else:
        turn_amount = Decimal("0")

    return {
        "id": account["id"],
        "name": account["name"],
        "liquidity": float(turn_amount),
        "incomes": float(active_turn_incomes) if active_turn else 0,
        "expenses": float(active_turn_expenses) if active_turn else 0,
        "history": history,
    }


def create_account(
    connection: Connection, *, name: str, initial_balance: Decimal | None = None
) -> dict:
    existing = accounts_repo.get_account_by_name(
        connection, name=name, include_inactive=True
    )
    if existing:
        raise AccountAlreadyExistsError("Account already exists")
    account = accounts_repo.create_account(
        connection, name=name, account_amount=initial_balance
    )
    if initial_balance and initial_balance > 0:
        # Create an initial closed turn to set the account's historical balance
        turn_group_id = uuid4()
        turns_repo.create_closed_turn(
            connection,
            account_id=account["id"],
            start_amount=Decimal("0"),
            end_amount=initial_balance,
            turn_group_id=turn_group_id,
        )
    # If there is an active global turn, create an open turn for this account in that group
    active_group = turns_repo.get_active_group_id(connection)
    if active_group:
        # start_amount should be the current account_amount (which includes initial_balance if set)
        current_amount = Decimal(str(account["account_amount"] or 0))
        turns_repo.create_turn(
            connection,
            account_id=account["id"],
            start_amount=current_amount,
            turn_group_id=active_group,
        )
    return account


def update_account(
    connection: Connection,
    *,
    account_id: UUID,
    name: str | None,
    account_amount: Decimal | None,
) -> dict:
    account = accounts_repo.get_account(
        connection, account_id=account_id, include_inactive=True
    )
    if account is None:
        raise AccountNotFoundError("Account not found")

    if name is not None:
        existing = accounts_repo.get_account_by_name(
            connection, name=name, include_inactive=True
        )
        if existing and existing["id"] != account_id:
            raise AccountAlreadyExistsError("Account already exists")

    if account_amount is not None:
        active_turn = turns_repo.get_active_turn(connection, account_id=account_id)
        if active_turn:
            raise AccountUpdateError("Cannot adjust amount while turn is open")
        turns = turns_repo.list_turns_for_account(connection, account_id=account_id)
        closed = [turn for turn in turns if turn["status"] == TurnStatus.CLOSED]
        if closed:
            latest = max(closed, key=lambda row: row["closed_at"] or row["created_at"])
            turns_repo.update_closed_turn_amount(
                connection, turn_id=latest["id"], end_amount=account_amount
            )
        else:
            turns_repo.create_closed_turn(
                connection,
                account_id=account_id,
                start_amount=account_amount,
                end_amount=account_amount,
                turn_group_id=uuid4(),
            )

    updated = accounts_repo.update_account(connection, account_id=account_id, name=name)
    if updated is None:
        raise AccountNotFoundError("Account not found")
    return _build_summary(connection, account_id=account_id)


def delete_account(
    connection: Connection,
    *,
    account_id: UUID,
    allow_nonzero: bool = False,
    hard_delete: bool = False,
) -> None:
    account = accounts_repo.get_account(
        connection, account_id=account_id, include_inactive=True
    )
    if account is None:
        raise AccountNotFoundError("Account not found")
    if not account.get("is_active", True) and not hard_delete:
        raise AccountDeletionError("Account already inactive")

    active_turn = turns_repo.get_active_turn(connection, account_id=account_id)
    if active_turn:
        turn_amount = _calculate_turn_amount(connection, turn=active_turn)
        if turn_amount != 0 and not allow_nonzero:
            raise AccountDeletionError("Active turn has non-zero balance")
    account_amount = _get_latest_closed_turn_amount(connection, account_id=account_id)
    if account_amount != 0 and not allow_nonzero:
        raise AccountDeletionError("Account has non-zero balance")

    deleted = accounts_repo.delete_account(
        connection, account_id=account_id, hard_delete=hard_delete
    )
    if not deleted:
        raise AccountNotFoundError("Account not found")
