from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.engine import Connection
from sqlalchemy import func, select  # <-- añadido select y func

from app.core.types import TurnStatus
from app.models.tables import turns
from app.repositories import accounts as accounts_repo
from app.repositories import movements as movement_repo
from app.repositories import turns as turns_repo


class TurnNotFoundError(ValueError):
    pass


class ActiveTurnExistsError(ValueError):
    pass


class GlobalTurnNotFoundError(ValueError):
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
    closed = [turn for turn in turns if turn["status"] == TurnStatus.CLOSED]
    if not closed:
        return Decimal("0")
    latest = max(closed, key=lambda row: row["closed_at"] or row["created_at"])
    return Decimal(latest["end_amount"] or 0)


def open_turn(connection: Connection, *, account_id: UUID) -> dict:
    account = accounts_repo.get_account(connection, account_id=account_id, include_inactive=True)
    if account is None:
        raise ValueError("Account not found")
    existing = turns_repo.get_active_turn(connection, account_id=account_id)
    if existing:
        raise ActiveTurnExistsError("Active turn already exists")
    # Usar el saldo actual de la cuenta como start_amount
    start_amount = Decimal(str(account.get("account_amount") or 0))
    return turns_repo.create_turn(
        connection,
        account_id=account_id,
        start_amount=start_amount,
        turn_group_id=uuid4(),
    )


def close_turn(connection: Connection, *, turn_id: UUID) -> dict:
    turn = turns_repo.get_turn(connection, turn_id=turn_id)
    if turn is None:
        raise TurnNotFoundError("Turn not found")
    if turn["status"] != TurnStatus.OPEN:
        raise ValueError("Turn is not open")

    end_amount = _calculate_turn_amount(connection, turn=turn)
    updated = turns_repo.close_turn(connection, turn_id=turn_id, end_amount=end_amount)
    if updated is None:
        raise TurnNotFoundError("Turn not found")
    movements_count = movement_repo.count_movements(connection, turn_id=turn_id)
    # Al cerrar el turno, actualizar account_amount al end_amount (consolida el saldo)
    from app.repositories import accounts as accounts_repo
    accounts_repo.update_account(
        connection, account_id=turn["account_id"], account_amount=end_amount
    )
    return {
        "turn_id": updated["id"],
        "end_amount": updated["end_amount"],
        "movements_count": movements_count,
    }


def get_active_turn(connection: Connection, *, account_id: UUID) -> dict:
    turn = turns_repo.get_active_turn(connection, account_id=account_id)
    if turn is None:
        raise TurnNotFoundError("No active turn")
    return {
        "turn_id": turn["id"],
        "start_amount": turn["start_amount"],
    }


def open_global_turn(connection: Connection) -> dict:
    active_group = turns_repo.get_active_group_id(connection)
    if active_group is not None:
        raise ActiveTurnExistsError("Active global turn already exists")
    accounts = accounts_repo.list_accounts(connection)
    if not accounts:
        raise ValueError("No accounts available")
    group_id = uuid4()
    opened_at = datetime.utcnow()
    for account in accounts:
        existing = turns_repo.get_active_turn(connection, account_id=account["id"])
        if existing:
            continue
        # Usar el saldo actual de la cuenta (account_amount) como start_amount
        start_amount = Decimal(str(account.get("account_amount") or 0))
        turns_repo.create_turn(
            connection,
            account_id=account["id"],
            start_amount=start_amount,
            turn_group_id=group_id,
        )
    return {
        "turn_group_id": group_id,
        "opened_at": opened_at,
        "status": TurnStatus.OPEN,
    }


def close_global_turn(connection: Connection) -> dict:
    active_group = turns_repo.get_active_group_id(connection)
    if active_group is None:
        raise GlobalTurnNotFoundError("No active global turn")
    turns = turns_repo.list_turns_by_group(
        connection, turn_group_id=active_group, status=TurnStatus.OPEN
    )
    if not turns:
        raise GlobalTurnNotFoundError("No active global turn")
    for turn in turns:
        end_amount = _calculate_turn_amount(connection, turn=turn)
        turns_repo.close_turn(connection, turn_id=turn["id"], end_amount=end_amount)
        # Al cerrar, actualizar account_amount al end_amount (consolida)
        from app.repositories import accounts as accounts_repo
        accounts_repo.update_account(
            connection, account_id=turn["account_id"], account_amount=end_amount
        )
    return {"turn_group_id": active_group, "status": TurnStatus.CLOSED}


def get_global_turn_summary(
    connection: Connection, *, account_id: UUID | None = None, turn_group_id: UUID | None = None
) -> dict:
    # Si se pasa turn_group_id, usar ese grupo específico
    if turn_group_id is not None:
        turns = turns_repo.list_turns_by_group(connection, turn_group_id=turn_group_id)
        if account_id is not None:
            turns = [turn for turn in turns if turn["account_id"] == account_id]
            if not turns:
                raise GlobalTurnNotFoundError("No turns for selected account")
    else:
        active_group = turns_repo.get_active_group_id(connection)
        group_id = active_group or turns_repo.get_latest_closed_group_id(connection)
        if group_id is None:
            raise GlobalTurnNotFoundError("No turns found")
        turns = turns_repo.list_turns_by_group(connection, turn_group_id=group_id)
        if account_id is not None:
            turns = [turn for turn in turns if turn["account_id"] == account_id]
            if not turns:
                raise GlobalTurnNotFoundError("No turns for selected account")
        turn_group_id = group_id

    if not turns:
        raise GlobalTurnNotFoundError("No turns found for the given criteria")

    start_total = sum(Decimal(turn["start_amount"]) for turn in turns)
    opened_at = min(turn["created_at"] for turn in turns)
    # Determinar estatus: si algún turno del grupo está abierto, el grupo está abierto
    status = TurnStatus.OPEN if any(t["status"] == TurnStatus.OPEN for t in turns) else TurnStatus.CLOSED
    incomes = Decimal("0")
    expenses = Decimal("0")
    transfer_in = Decimal("0")
    transfer_out = Decimal("0")
    for turn in turns:
        sums = movement_repo.get_movement_sums(connection, turn_id=turn["id"])
        incomes += sums["income"]
        expenses += sums["expense"]
        transfer_in += sums["transfer_in"]
        transfer_out += sums["transfer_out"]
    liquidity = start_total + incomes - expenses + (transfer_in - transfer_out)

    # Credit totals (devengo, cxc, cxp) no dependen del turn_group, son globales o por cuenta
    from app.repositories import credits as credits_repo
    credit_totals = credits_repo.get_credit_summary(connection, account_id=account_id)
    turn_devengo = credit_totals["devengo_total"]
    turn_cxc = credit_totals["cxc_total"]
    turn_cxp = credit_totals["cxp_total"]

    return {
        "turn_group_id": turn_group_id,
        "status": status,
        "opened_at": opened_at,
        "liquidity": liquidity,
        "incomes": incomes,
        "expenses": expenses,
        "turn_devengo": turn_devengo,
        "turn_cxc": turn_cxc,
        "turn_cxp": turn_cxp,
    }


def get_historical_summary(connection: Connection) -> dict:
    """Resumen histórico total: liquidez (saldo total de cuentas), ingresos, egresos, cxc, cxp."""
    from app.repositories import accounts as accounts_repo
    from app.repositories import credits as credits_repo
    from app.core.types import MovementType
    from sqlalchemy import func
    from decimal import Decimal
    from app.models.tables import movements, turns
    from uuid import uuid4
    from datetime import datetime

    # 1. Liquidez: suma de account_amount de cuentas activas
    accounts = accounts_repo.list_accounts(connection, include_inactive=False)
    liquidity = Decimal("0")
    if accounts:
        for acc in accounts:
            amt = acc.get("account_amount")
            if amt is not None:
                try:
                    liquidity += Decimal(str(amt))
                except Exception:
                    pass

    # 2. Ingresos y egresos totales de movimientos activos
    stmt = select(
        func.sum(movements.c.amount).filter(movements.c.type == MovementType.INGRESO).label("income"),
        func.sum(movements.c.amount).filter(movements.c.type == MovementType.EGRESO).label("expense"),
    ).select_from(movements).where(movements.c.is_active.is_(True))
    result = connection.execute(stmt)
    row = result.first()
    income = Decimal(str(row.income or 0))
    expense = Decimal(str(row.expense or 0))

    # 3. CxC y CxP pendientes (todos los créditos no pagados)
    credit_totals = credits_repo.get_credit_summary(connection, account_id=None)
    cxc_total = Decimal(str(credit_totals.get("cxc_total") or 0))
    cxp_total = Decimal(str(credit_totals.get("cxp_total") or 0))

    devengo = income - expense

    # 4. turn_group_id y opened_at para cumplir schema (usamos valores existentes o dummy)
    active_group = turns_repo.get_active_group_id(connection)
    if active_group:
        group_id = active_group
    else:
        group_id = turns_repo.get_latest_closed_group_id(connection) or uuid4()

    # Buscar el turno más antiguo del grupo para opened_at, o usar ahora
    if group_id:
        turns_list = turns_repo.list_turns_by_group(connection, turn_group_id=group_id)
        if turns_list:
            opened_at = min(turn["created_at"] for turn in turns_list)
        else:
            opened_at = datetime.utcnow()
    else:
        opened_at = datetime.utcnow()

    return {
        "turn_group_id": str(group_id) if group_id else None,
        "status": "CLOSED",
        "opened_at": opened_at,
        "liquidity": float(liquidity),
        "incomes": float(income),
        "expenses": float(expense),
        "turn_devengo": float(devengo),
        "turn_cxc": float(cxc_total),
        "turn_cxp": float(cxp_total),
    }


def list_turn_groups(connection: Connection) -> list[dict]:
    from sqlalchemy import select, func, distinct

    stmt = (
        select(
            turns.c.turn_group_id,
            func.min(turns.c.created_at).label("opened_at"),
            func.max(turns.c.closed_at).label("closed_at"),
            func.count(distinct(turns.c.account_id)).label("account_count"),
            func.bool_or(turns.c.status == TurnStatus.OPEN).label("has_open"),
        )
        .group_by(turns.c.turn_group_id)
        .order_by(func.min(turns.c.created_at).desc())
    )
    result = connection.execute(stmt)
    groups = []
    for row in result.mappings():
        groups.append(
            {
                "turn_group_id": row["turn_group_id"],
                "opened_at": row["opened_at"],
                "closed_at": row["closed_at"],
                "account_count": row["account_count"],
                "status": "OPEN" if row["has_open"] else "CLOSED",
            }
        )
    return groups

