from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.engine import Connection

from app.repositories import credits as credits_repo
from app.repositories import movements as movement_repo
from app.repositories import turns as turns_repo
from app.services import movements as movement_service
from app.core.types import CreditType, CreditStatus


class CreditError(ValueError):
    pass


def create_credit(
    connection: Connection,
    *,
    type: CreditType,
    total_amount: Decimal,
    due_date: datetime,
    description: str | None = None,
    account_id: UUID | None = None,
) -> dict:
    # Asignar una cuenta activa por defecto si no se proporciona
    if account_id is None:
        from sqlalchemy import select
        from app.models.tables import accounts
        stmt = select(accounts.c.id).where(accounts.c.is_active.is_(True)).limit(1)
        result = connection.execute(stmt).first()
        if result:
            account_id = result[0]
        else:
            raise CreditError("No hay cuenta activa para asignar al crédito")
    # No create movement now. Devengo se contabiliza en resumen separado.
    credit = credits_repo.create_credit(
        connection,
        account_id=account_id,
        type=type.value,
        total_amount=total_amount,
        due_date=due_date,
        description=description,
    )
    return credit


def pay_credit(
    connection: Connection,
    *,
    credit_id: UUID,
    amount: Decimal,
    account_id: UUID,
    description: str | None = None,
) -> dict:
    # Validate and update credit
    credit_before = credits_repo.get_credit(connection, credit_id=credit_id)
    if credit_before is None:
        raise CreditError("Credit not found")
    if credit_before["status"] == "PAGADO":
        raise CreditError("Credit already paid")

    new_total_paid = credit_before["paid_amount"] + amount
    if new_total_paid > credit_before["total_amount"]:
        raise CreditError("Payment exceeds remaining amount")

    # Determine new status
    if new_total_paid == credit_before["total_amount"]:
        new_status = "PAGADO"
    else:
        new_status = "PARCIAL"

    # Update credit
    updated = credits_repo.pay_credit(
        connection,
        credit_id=credit_id,
        amount=amount,
        description=description,
    )

    # Create real movement for cash flow (liquidity) in the provided account
    turn = turns_repo.get_active_turn(connection, account_id=account_id)
    if turn is None:
        raise CreditError("No active turn")

    if credit_before["type"] == CreditType.CREDIT_SALE:
        movement_type = "INCOME"
    else:
        movement_type = "EXPENSE"

    movement = movement_repo.create_movement(
        connection,
        turn_id=turn["id"],
        movement_type=movement_type,
        amount=amount,
        description=description or ("Cobro de crédito" if credit_before["type"] == CreditType.CREDIT_SALE else "Pago de deuda"),
    )

    # Return updated credit (router expects {"credit": ...})
    return {"credit": updated}


def update_credit(
    connection: Connection,
    *,
    credit_id: UUID,
    total_amount: Decimal | None = None,
    due_date: datetime | None = None,
    description: str | None = None,
) -> dict:
    credit = credits_repo.update_credit(
        connection,
        credit_id=credit_id,
        total_amount=total_amount,
        due_date=due_date,
        description=description,
    )
    if credit is None:
        raise CreditError("Credit not found")
    return credit


def list_credits(
    connection: Connection,
    *,
    account_id: UUID | None = None,
    status: str | None = None,
) -> list[dict]:
    return credits_repo.list_credits(connection, account_id=account_id, status=status)


def get_credit_summary(connection: Connection, *, account_id: UUID | None = None) -> dict:
    return credits_repo.get_credit_summary(connection, account_id=account_id)


def get_turn_summary_with_credits(
    connection: Connection, *, account_id: UUID | None = None
) -> dict:
    """Returns global turn summary extended with devengo, cxc, cxp."""
    # Original summary (liquidity, incomes, expenses from movements)
    summary = turns_repo.get_global_turn_summary(connection, account_id=account_id)

    # Add credit totals
    credit_totals = get_credit_summary(connection, account_id=account_id)
    summary["turn_devengo"] = credit_totals["devengo_total"]
    summary["turn_cxc"] = credit_totals["cxc_total"]
    summary["turn_cxp"] = credit_totals["cxp_total"]
    return summary
