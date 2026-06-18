from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import sqlite3
import io
import os
from decimal import Decimal
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection
from app.config import DATABASE_URL
from app.database import engine
from app.models.tables import metadata

print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", flush=True)
print("[ADMIN] MODULE LOADED", flush=True)
print(f"[ADMIN] DATABASE_URL: {DATABASE_URL}", flush=True)
print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", flush=True)

router = APIRouter(prefix="/admin", tags=["admin"])

# === Autenticación por header ===
def verify_admin_password(request: Request) -> bool:
    """Verifica que el header X-Admin-Password coincida con ADMIN_PASSWORD."""
    password = request.headers.get("X-Admin-Password")
    expected = os.getenv("ADMIN_PASSWORD", "")
    return password == expected

def require_admin_password(request: Request):
    """Dependency que raise 401 si la contraseña no es válida."""
    if not verify_admin_password(request):
        raise HTTPException(status_code=401, detail="Contraseña administrativa inválida")
    return True

# === Backup ===
@router.get("/backup-db")
def backup_db(admin_auth=Depends(require_admin_password)):
    """
    Genera un dump SQL de la base de datos (SQLite) y lo devuelve como archivo de descarga.
    """
    # Usar la base de datos configurada en el engine (sqlite)
    db_path = engine.url.database  # e.g., 'ferrega.db' (relative to cwd)
    try:
        conn = sqlite3.connect(db_path)
        with io.StringIO() as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
            conn.close()
            content = f.getvalue()
        filename = f"ferrega_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando backup: {str(e)}")

# === Lista de tablas ===
@router.get("/tables")
def list_tables(request: Request, admin_auth=Depends(require_admin_password)):
    """
    Devuelve la lista de tablas de la base de datos.
    """
    try:
        insp = inspect(engine)
        table_names = insp.get_table_names()
        return {"tables": table_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando tablas: {str(e)}")

# === Rows dinámicos con filtros y paginación ===
@router.post("/table/{table}/rows")
async def list_table_rows(
    table: str,
    request: Request,
    admin_auth=Depends(require_admin_password)
):
    """
    Obtiene filas de una tabla con filtros (ilike) y paginación (skip/limit).
    Body: { filters: {col: value}, skip: int, limit: int }
    Retorna: { rows: [...], columns: [...], total: int }
    """
    payload = await request.json() or {}
    filters = payload.get("filters", {})
    skip = int(payload.get("skip", 0))
    limit = int(payload.get("limit", 50))

    # Validar que la tabla existe en metadata
    if table not in metadata.tables:
        raise HTTPException(status_code=404, detail=f"Tabla '{table}' no encontrada")

    tbl = metadata.tables[table]
    columns = [c.name for c in tbl.columns]

    # Construir consulta base
    stmt = select(tbl)

    # Aplicar filtros ilike por columna
    for col_name, value in filters.items():
        if col_name in columns and value:
            col = tbl.c[col_name]
            # Para SQLite: usar LIKE (case-insensitive depende de configuración)
            # Para PostgreSQL: usar ilike
            if DATABASE_URL.startswith("postgresql"):
                stmt = stmt.where(col.ilike(f"%{value}%"))
            else:
                stmt = stmt.where(col.like(f"%{value}%"))

    # Obtener total antes de paginación
    try:
        with engine.connect() as conn:
            total_conn = conn.execute(select(tbl).where(*[tbl.c[col].ilike(f"%{value}%") if DATABASE_URL.startswith("postgresql") else tbl.c[col].like(f"%{value}%") for col, value in filters.items() if col in columns and value]))
            total = len(total_conn.fetchall())
    except Exception:
        # Fallback: contar sin filtros si falla
        try:
            with engine.connect() as conn:
                total = len(conn.execute(select(tbl)).fetchall())
        except Exception:
            total = 0

    # Aplicar paginación
    stmt = stmt.offset(skip).limit(limit)

    try:
        with engine.connect() as conn:
            result = conn.execute(stmt)
            rows_raw = result.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando {table}: {str(e)}")

    # Convertir filas a dict, serializando tipos no JSON a string
    rows = []
    for row in rows_raw:
        row_dict = {}
        for col in columns:
            val = getattr(row, col)
            if val is None:
                row_dict[col] = None
            else:
                # Convertir tipos no nativos a JSON
                if isinstance(val, Decimal):
                    row_dict[col] = str(val)
                elif isinstance(val, (bytes, memoryview)):
                    row_dict[col] = val.hex()
                elif hasattr(val, "__dict__"):  # UUID, etc.
                    row_dict[col] = str(val)
                else:
                    row_dict[col] = val
        rows.append(row_dict)

    return {"rows": rows, "columns": columns, "total": total}

# === Crear registro ===
@router.post("/table/{table}/row")
async def create_row(
    table: str,
    request: Request,
    admin_auth=Depends(require_admin_password)
):
    """
    Crea un nuevo registro en la tabla.
    Body: { col1: val1, col2: val2, ... }
    Retorna: { success: true, id: <new_id> }
    """
    payload = await request.json() or {}
    if table not in metadata.tables:
        raise HTTPException(status_code=404, detail=f"Tabla '{table}' no encontrada")
    tbl = metadata.tables[table]
    # Construir INSERT
    try:
        with engine.begin() as conn:
            result = conn.execute(tbl.insert().values(**payload))
            new_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
        return {"success": True, "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creando registro: {str(e)}")

# === Actualizar registro ===
@router.patch("/table/{table}/{row_id}")
async def update_row(
    table: str,
    row_id: str,
    request: Request,
    admin_auth=Depends(require_admin_password)
):
    """
    Actualiza un registro por ID.
    Body: { col1: newval1, ... }
    Retorna: { success: true }
    """
    payload = await request.json() or {}
    if table not in metadata.tables:
        raise HTTPException(status_code=404, detail=f"Tabla '{table}' no encontrada")
    tbl = metadata.tables[table]
    # Encontrar columna PK
    pk_cols = [c for c in tbl.primary_key.columns]
    if not pk_cols:
        raise HTTPException(status_code=500, detail=f"Tabla '{table}' no tiene PK definida")
    pk_col = pk_cols[0].name
    try:
        with engine.begin() as conn:
            stmt = tbl.update().where(tbl.c[pk_col] == row_id).values(**payload)
            result = conn.execute(stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error actualizando registro: {str(e)}")

# === Eliminar registro ===
@router.delete("/table/{table}/{row_id}")
def delete_row(
    table: str,
    row_id: str,
    request: Request,
    admin_auth=Depends(require_admin_password)
):
    """
    Elimina un registro por ID.
    Retorna: { success: true }
    """
    if table not in metadata.tables:
        raise HTTPException(status_code=404, detail=f"Tabla '{table}' no encontrada")
    tbl = metadata.tables[table]
    pk_cols = [c for c in tbl.primary_key.columns]
    if not pk_cols:
        raise HTTPException(status_code=500, detail=f"Tabla '{table}' no tiene PK definida")
    pk_col = pk_cols[0].name
    try:
        with engine.begin() as conn:
            stmt = tbl.delete().where(tbl.c[pk_col] == row_id)
            result = conn.execute(stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error eliminando registro: {str(e)}")
