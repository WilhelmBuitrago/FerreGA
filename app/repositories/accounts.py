from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection

from app.models.tables import accounts


def create_account(connection: Connection, *, name: str, account_amount: Decimal | None = None) -> dict:
    result = connection.execute(
        insert(accounts)
        .values(id=uuid4(), name=name, account_amount=account_amount or 0)
        .returning(
            accounts.c.id,
            accounts.c.name,
            accounts.c.account_amount,
        )
    )
    return result.mappings().one()


def get_account(
    connection: Connection, *, account_id: UUID, include_inactive: bool = False
) -> dict | None:
    query = select(
        accounts.c.id,
        accounts.c.name,
        accounts.c.account_amount,
        accounts.c.is_active,
    ).where(accounts.c.id == account_id)
    if not include_inactive:
        query = query.where(accounts.c.is_active.is_(True))
    result = connection.execute(query)
    return result.mappings().one_or_none()


def get_account_by_name(
    connection: Connection, *, name: str, include_inactive: bool = False
) -> dict | None:
    query = select(
        accounts.c.id,
        accounts.c.name,
        accounts.c.account_amount,
        accounts.c.is_active,
    ).where(accounts.c.name == name)
    if not include_inactive:
        query = query.where(accounts.c.is_active.is_(True))
    result = connection.execute(query)
    return result.mappings().one_or_none()


def list_accounts(
    connection: Connection, *, include_inactive: bool = False
) -> list[dict]:
    query = select(
        accounts.c.id,
        accounts.c.name,
        accounts.c.account_amount,
        accounts.c.turn_amount,
        accounts.c.difference,
        accounts.c.is_active,
    ).order_by(accounts.c.name)
    if not include_inactive:
        query = query.where(accounts.c.is_active.is_(True))
    result = connection.execute(query)
    return list(result.mappings().all())


def delete_account(
    connection: Connection, *, account_id: UUID, hard_delete: bool = False
) -> bool:
    if hard_delete:
        result = connection.execute(delete(accounts).where(accounts.c.id == account_id))
    else:
        result = connection.execute(
            update(accounts).where(accounts.c.id == account_id).values(is_active=False)
        )
    return result.rowcount > 0


def update_account(
    connection: Connection, *, account_id: UUID, name: str | None = None, account_amount: Decimal | None = None
) -> dict | None:
    values: dict = {}
    if name is not None:
        values["name"] = name
    if account_amount is not None:
        values["account_amount"] = account_amount
    if not values:
        return get_account(connection, account_id=account_id, include_inactive=True)

    result = connection.execute(
        update(accounts)
        .where(accounts.c.id == account_id)
        .values(**values)
        .returning(
            accounts.c.id,
            accounts.c.name,
            accounts.c.account_amount,
            accounts.c.is_active,
        )
    )
    return result.mappings().one_or_none()
