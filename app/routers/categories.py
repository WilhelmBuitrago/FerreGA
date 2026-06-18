from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection
from sqlalchemy import select

from app.database import get_connection
from app.models.tables import categorias

router = APIRouter(prefix="/categories", tags=["categories"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.get("")
def list_categories(connection: Connection = Depends(get_db)):
    stmt = select(
        categorias.c.codigo,
        categorias.c.nombre,
        categorias.c.tipo,
        categorias.c.grupo,
    ).where(categorias.c.activo.is_(True)).order_by(categorias.c.tipo, categorias.c.grupo, categorias.c.nombre)
    result = connection.execute(stmt)
    categories = [
        {
            "codigo": row.codigo,
            "nombre": row.nombre,
            "tipo": row.tipo,
            "grupo": row.grupo,
        }
        for row in result.mappings()
    ]
    return {"categories": categories}
