from __future__ import annotations

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from app.models.tables import usuarios


def get_user_by_id(connection: Connection, *, user_id: str) -> dict | None:
    result = connection.execute(
        select(
            usuarios.c.id,
            usuarios.c.nombre,
            usuarios.c.password_hash,
            usuarios.c.role,
        ).where(usuarios.c.id == user_id)
    )
    return result.mappings().one_or_none()


def create_user(
    connection: Connection,
    *,
    user_id: str,
    name: str,
    password_hash: str,
    role: str,
) -> dict:
    result = connection.execute(
        insert(usuarios)
        .values(id=user_id, nombre=name, password_hash=password_hash, role=role)
        .returning(usuarios.c.id, usuarios.c.nombre, usuarios.c.role)
    )
    return result.mappings().one()


def update_user_credentials(
    connection: Connection,
    *,
    user_id: str,
    password_hash: str,
    role: str,
) -> dict | None:
    result = connection.execute(
        update(usuarios)
        .where(usuarios.c.id == user_id)
        .values(password_hash=password_hash, role=role)
        .returning(usuarios.c.id, usuarios.c.nombre, usuarios.c.role)
    )
    return result.mappings().one_or_none()
