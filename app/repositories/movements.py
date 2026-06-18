from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.engine import Connection

from app.core.types import MovementType
from app.models.tables import accounts, movements, turns


def create_movement(
    connection: Connection,
    *,
    turn_id: UUID,
    movement_type: MovementType,
    amount: Decimal,
    description: str | None,
    category_code: str | None = None,
    is_outgoing: bool = False,
) -> dict:
    # Si se proporciona category_code, validar que existe y está activa
    if category_code is not None:
        from app.models.tables import categorias
        cat_stmt = select(categorias.c.activo).where(categorias.c.codigo == category_code)
        cat_result = connection.execute(cat_stmt).first()
        if not cat_result or not cat_result.activo:
            from app.services.movements import MovementError
            raise MovementError(f"Categoría '{category_code}' no existe o no está activa")
    from uuid import uuid4
    result = connection.execute(
        insert(movements)
        .values(
            id=uuid4(),
            turn_id=turn_id,
            type=movement_type,
            amount=amount,
            description=description,
            categoria_codigo=category_code,
            is_outgoing=is_outgoing,
        )
        .returning(
            movements.c.id,
            movements.c.turn_id,
            movements.c.type,
            movements.c.amount,
            movements.c.description,
            movements.c.timestamp,
            movements.c.is_outgoing,
        )
    )
    return result.mappings().one()


def list_movements_by_turn(connection: Connection, *, turn_id: UUID) -> list[dict]:
    result = connection.execute(
        select(
            movements.c.id,
            movements.c.turn_id,
            movements.c.type,
            movements.c.amount,
            movements.c.description,
            movements.c.categoria_codigo,
            movements.c.timestamp,
            movements.c.is_outgoing,
        )
        .where(movements.c.turn_id == turn_id, movements.c.is_active.is_(True))
        .order_by(movements.c.timestamp.asc())
    )
    return list(result.mappings().all())


def get_movement(connection: Connection, *, movement_id: UUID) -> dict | None:
    result = connection.execute(
        select(
            movements.c.id,
            movements.c.turn_id,
            movements.c.type,
            movements.c.amount,
            movements.c.description,
            movements.c.timestamp,
            movements.c.is_outgoing,
            movements.c.is_active,
        ).where(movements.c.id == movement_id)
    )
    return result.mappings().one_or_none()


def update_movement(
    connection: Connection,
    *,
    movement_id: UUID,
    amount: Decimal | None,
    description: str | None,
) -> dict | None:
    values: dict = {}
    if amount is not None:
        values["amount"] = amount
    if description is not None:
        values["description"] = description
    if not values:
        return get_movement(connection, movement_id=movement_id)
    result = connection.execute(
        update(movements)
        .where(movements.c.id == movement_id)
        .values(**values)
        .returning(
            movements.c.id,
            movements.c.turn_id,
            movements.c.type,
            movements.c.amount,
            movements.c.description,
            movements.c.timestamp,
            movements.c.is_outgoing,
            movements.c.is_active,
        )
    )
    return result.mappings().one_or_none()


def soft_delete_movement(connection: Connection, *, movement_id: UUID) -> bool:
    result = connection.execute(
        update(movements).where(movements.c.id == movement_id).values(is_active=False)
    )
    return result.rowcount > 0


def get_movement_sums(connection: Connection, *, turn_id: UUID) -> dict:
    income_sum = func.coalesce(
        func.sum(movements.c.amount).filter(movements.c.type == MovementType.INGRESO),
        0,
    )

    expense_sum = func.coalesce(
        func.sum(movements.c.amount).filter(movements.c.type == MovementType.EGRESO),
        0,
    )

    transfer_in_sum = func.coalesce(
        func.sum(movements.c.amount).filter(
            (movements.c.type == MovementType.TRANSFERENCIA)
            & (movements.c.is_outgoing.is_(False))
        ),
        0,
    )

    transfer_out_sum = func.coalesce(
        func.sum(movements.c.amount).filter(
            (movements.c.type == MovementType.TRANSFERENCIA)
            & (movements.c.is_outgoing.is_(True))
        ),
        0,
    )

    result = connection.execute(
        select(
            income_sum.label("income"),
            expense_sum.label("expense"),
            transfer_in_sum.label("transfer_in"),
            transfer_out_sum.label("transfer_out"),
        ).where(
            movements.c.turn_id == turn_id,
            movements.c.is_active.is_(True),
        )
    )

    row = result.first()
    if row is None:
        return {
            "income": Decimal("0"),
            "expense": Decimal("0"),
            "transfer_in": Decimal("0"),
            "transfer_out": Decimal("0"),
        }
    return {
        "income": Decimal(row.income or 0),
        "expense": Decimal(row.expense or 0),
        "transfer_in": Decimal(row.transfer_in or 0),
        "transfer_out": Decimal(row.transfer_out or 0),
    }


def count_movements(connection: Connection, *, turn_id: UUID) -> int:
    result = connection.execute(
        select(func.count(movements.c.id)).where(
            movements.c.turn_id == turn_id, movements.c.is_active.is_(True)
        )
    )
    count = result.scalar_one()
    return int(count)


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
    query = (
        select(
            movements.c.id,
            movements.c.type,
            movements.c.amount,
            movements.c.description,
            movements.c.categoria_codigo,
            movements.c.timestamp,
            movements.c.is_outgoing,
            turns.c.id.label("turn_id"),
            turns.c.turn_group_id,
            accounts.c.id.label("account_id"),
            accounts.c.name.label("account_name"),
        )
        .select_from(movements.join(turns).join(accounts))
        .where(movements.c.is_active.is_(True))
    )

    if turn_group_id is not None:
        query = query.where(turns.c.turn_group_id == turn_group_id)
    if account_id is not None:
        query = query.where(accounts.c.id == account_id)
    if movement_type is not None:
        query = query.where(movements.c.type == movement_type)
    if amount_min is not None:
        query = query.where(movements.c.amount >= amount_min)
    if amount_max is not None:
        query = query.where(movements.c.amount <= amount_max)
    if description_regex:
        query = query.where(movements.c.description.op("~*")(description_regex))
    if start_date is not None:
        query = query.where(movements.c.timestamp >= start_date)
    if end_date is not None:
        query = query.where(movements.c.timestamp <= end_date)

    result = connection.execute(
        query.order_by(movements.c.timestamp.desc()).offset(skip).limit(limit)
    )
    return list(result.mappings().all())
