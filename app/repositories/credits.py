from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update, insert
from sqlalchemy.engine import Connection

from app.models.tables import credits as credits_table


def create_credit(
    connection: Connection,
    *,
    account_id: UUID | None = None,
    type: str,
    total_amount: Decimal,
    due_date: datetime,
    description: str | None = None,
) -> dict:
    result = connection.execute(
        insert(credits_table)
        .values(
            account_id=account_id,
            type=type,
            total_amount=total_amount,
            paid_amount=Decimal("0"),
            due_date=due_date,
            status="PENDIENTE",
            description=description,
        )
        .returning(
            credits_table.c.id,
            credits_table.c.account_id,
            credits_table.c.type,
            credits_table.c.total_amount,
            credits_table.c.paid_amount,
            credits_table.c.due_date,
            credits_table.c.status,
            credits_table.c.description,
            credits_table.c.created_at,
            credits_table.c.updated_at,
        )
    )
    row = result.mappings().one()
    row_dict = dict(row)
    row_dict["categoria"] = "CxC (Activo)" if type == "CREDIT_SALE" else "CxP (Pasivo)"
    return row_dict


def get_credit(connection: Connection, *, credit_id: UUID) -> dict | None:
    result = connection.execute(
        select(
            credits_table.c.id,
            credits_table.c.account_id,
            credits_table.c.type,
            credits_table.c.total_amount,
            credits_table.c.paid_amount,
            credits_table.c.due_date,
            credits_table.c.status,
            credits_table.c.description,
            credits_table.c.created_at,
            credits_table.c.updated_at,
        ).where(credits_table.c.id == credit_id)
    )
    row = result.mappings().one_or_none()
    if row:
        row_dict = dict(row)
        row_dict["categoria"] = "CxC (Activo)" if row_dict["type"] == "CREDIT_SALE" else "CxP (Pasivo)"
        return row_dict
    return None


def list_credits(
    connection: Connection,
    *,
    account_id: UUID | None = None,
    status: str | None = None,
) -> list[dict]:
    query = select(
        credits_table.c.id,
        credits_table.c.account_id,
        credits_table.c.type,
        credits_table.c.total_amount,
        credits_table.c.paid_amount,
        credits_table.c.due_date,
        credits_table.c.status,
        credits_table.c.description,
        credits_table.c.created_at,
        credits_table.c.updated_at,
    )
    if account_id is not None:
        query = query.where(credits_table.c.account_id == account_id)
    if status is not None:
        query = query.where(credits_table.c.status == status)
    query = query.order_by(credits_table.c.due_date.asc())
    result = connection.execute(query)
    rows = result.mappings().all()
    return [
        {**dict(row), "categoria": "CxC (Activo)" if row["type"] == "CREDIT_SALE" else "CxP (Pasivo)"}
        for row in rows
    ]


def pay_credit(
    connection: Connection,
    *,
    credit_id: UUID,
    amount: Decimal,
    description: str | None = None,
) -> dict:
    credit = get_credit(connection, credit_id=credit_id)
    if credit is None:
        raise ValueError("Credit not found")
    if credit["status"] == "PAGADO":
        raise ValueError("Credit already paid")
    new_paid = credit["paid_amount"] + amount
    if new_paid > credit["total_amount"]:
        raise ValueError("Payment exceeds remaining amount")
    new_status = "PAGADO" if new_paid == credit["total_amount"] else "PARCIAL"

    result = connection.execute(
        update(credits_table)
        .where(credits_table.c.id == credit_id)
        .values(
            paid_amount=new_paid,
            status=new_status,
            updated_at=func.now(),
        )
        .returning(
            credits_table.c.id,
            credits_table.c.account_id,
            credits_table.c.type,
            credits_table.c.total_amount,
            credits_table.c.paid_amount,
            credits_table.c.due_date,
            credits_table.c.status,
            credits_table.c.description,
            credits_table.c.created_at,
            credits_table.c.updated_at,
        )
    )
    row = result.mappings().one()
    row_dict = dict(row)
    row_dict["categoria"] = "CxC (Activo)" if row_dict["type"] == "CREDIT_SALE" else "CxP (Pasivo)"
    return row_dict


def get_credit_summary(connection: Connection, *, account_id: UUID | None = None) -> dict:
    """Calcula totales de CxC, CxP y devengo para una cuenta o global."""
    query = select(
        credits_table.c.type,
        credits_table.c.total_amount,
        credits_table.c.paid_amount,
    )
    if account_id is not None:
        query = query.where(credits_table.c.account_id == account_id)
    result = connection.execute(query)
    cxc_total = Decimal("0")
    cxp_total = Decimal("0")
    devengo_total = Decimal("0")
    total_ventas = Decimal("0")
    total_compras = Decimal("0")
    for row in result:
        if row.type == "CREDIT_SALE":
            cxc_total += row.total_amount - row.paid_amount
            total_ventas += row.total_amount
        elif row.type == "CREDIT_PURCHASE":
            cxp_total += row.total_amount - row.paid_amount
            total_compras += row.total_amount
    devengo_total = total_ventas - total_compras
    return {
        "cxc_total": cxc_total,
        "cxp_total": cxp_total,
        "devengo_total": devengo_total,
    }


def update_credit(
    connection: Connection,
    *,
    credit_id: UUID,
    total_amount: Decimal | None = None,
    due_date: datetime | None = None,
    description: str | None = None,
) -> dict | None:
    credit = get_credit(connection, credit_id=credit_id)
    if credit is None:
        return None
    values = {}
    if total_amount is not None:
        values["total_amount"] = total_amount
    if due_date is not None:
        values["due_date"] = due_date
    if description is not None:
        values["description"] = description
    if not values:
        return credit
    result = connection.execute(
        update(credits_table)
        .where(credits_table.c.id == credit_id)
        .values(**values)
        .returning(
            credits_table.c.id,
            credits_table.c.account_id,
            credits_table.c.type,
            credits_table.c.total_amount,
            credits_table.c.paid_amount,
            credits_table.c.due_date,
            credits_table.c.status,
            credits_table.c.description,
            credits_table.c.created_at,
            credits_table.c.updated_at,
        )
    )
    row = result.mappings().one()
    row_dict = dict(row)
    row_dict["categoria"] = "CxC (Activo)" if row_dict["type"] == "CREDIT_SALE" else "CxP (Pasivo)"
    return row_dict
