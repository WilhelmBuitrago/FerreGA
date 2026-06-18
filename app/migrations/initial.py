"""Initial database migrations and seed data.

These functions run once at application startup to ensure schema is up-to-date
and default data is present. They are designed to be idempotent.
"""

from sqlalchemy import inspect, text
from app.models.tables import metadata, categorias


def migrate_movements_table(conn):
    """Agrega la columna categoria_codigo a la tabla movements si no existe, y asigna categorías por defecto a movimientos existentes."""
    insp = inspect(conn)
    columns = [col["name"] for col in insp.get_columns("movements")]
    if "categoria_codigo" not in columns:
        conn.execute(text("ALTER TABLE movements ADD COLUMN categoria_codigo VARCHAR"))
    # Asignar categoría por defecto a movimientos existentes sin categoría
    conn.execute(text("UPDATE movements SET categoria_codigo = 'ING-OTROS' WHERE categoria_codigo IS NULL AND type = 'INGRESO'"))
    conn.execute(text("UPDATE movements SET categoria_codigo = 'GAS-OTROS' WHERE categoria_codigo IS NULL AND type = 'EGRESO'"))


def migrate_categorias_table(conn):
    """Agrega la columna grupo a la tabla categorias si no existe."""
    insp = inspect(conn)
    columns = [col["name"] for col in insp.get_columns("categorias")]
    if "grupo" not in columns:
        conn.execute(text("ALTER TABLE categorias ADD COLUMN grupo VARCHAR"))


def seed_default_categories(conn):
    """Inserta las categorías predeterminadas si no existen."""
    from sqlalchemy import select, insert, update
    from uuid import uuid4
    default_categories = [
        # INGRESOS
        {"codigo": "ING-VENTAS-CTO", "nombre": "Ventas contado", "tipo": "INGRESO", "grupo": "Ventas de productos"},
        {"codigo": "ING-VENTAS-CRED", "nombre": "Ventas crédito", "tipo": "INGRESO", "grupo": "Ventas de productos"},
        {"codigo": "ING-TRANSPORTE", "nombre": "Ingresos por transporte", "tipo": "INGRESO", "grupo": "Ventas de productos"},
        {"codigo": "ING-FINANCIEROS", "nombre": "Ingresos financieros", "tipo": "INGRESO", "grupo": "Financieros"},
        {"codigo": "ING-OTROS", "nombre": "Otros ingresos", "tipo": "INGRESO", "grupo": "Otros ingresos"},
        # GASTOS
        {"codigo": "GAS-COMPRA-MERC", "nombre": "Compra de mercancía", "tipo": "GASTO", "grupo": "Costos del negocio"},
        {"codigo": "GAS-TRANSP-MERC", "nombre": "Transporte de mercancía", "tipo": "GASTO", "grupo": "Costos del negocio"},
        {"codigo": "GAS-COSTOS", "nombre": "Costos del negocio", "tipo": "GASTO", "grupo": "Costos del negocio"},
        {"codigo": "GAS-OPER-ARREN", "nombre": "Arriendo", "tipo": "GASTO", "grupo": "Costos Operativos"},
        {"codigo": "GAS-OPER-SERV-PUB", "nombre": "Servicios públicos", "tipo": "GASTO", "grupo": "Costos Operativos"},
        {"codigo": "GAS-OPER-NOMINA", "nombre": "Nómina", "tipo": "GASTO", "grupo": "Costos Operativos"},
        {"codigo": "GAS-OPER-OTROS", "nombre": "Otros gastos operativos", "tipo": "GASTO", "grupo": "Costos Operativos"},
        {"codigo": "GAS-ADMIN-SOFT", "nombre": "Software", "tipo": "GASTO", "grupo": "Administrativos"},
        {"codigo": "GAS-ADMIN-HONOR", "nombre": "Honorarios", "tipo": "GASTO", "grupo": "Administrativos"},
        {"codigo": "GAS-ADMIN-OTROS", "nombre": "Otros gastos administrativos", "tipo": "GASTO", "grupo": "Administrativos"},
        {"codigo": "GAS-FIN-INTERESES", "nombre": "Intereses", "tipo": "GASTO", "grupo": "Financieros"},
        {"codigo": "GAS-FIN-COMISIONES", "nombre": "Comisiones (incluye 4x1000)", "tipo": "GASTO", "grupo": "Financieros"},
        {"codigo": "GAS-FIN-OTROS", "nombre": "Otros gastos financieros", "tipo": "GASTO", "grupo": "Financieros"},
        {"codigo": "GAS-OTROS", "nombre": "Otros gastos", "tipo": "GASTO", "grupo": "Otros gastos"},
        # PASIVOS
        {"codigo": "PAS-CXP", "nombre": "Cuentas por pagar", "tipo": "PASIVO", "grupo": None},
        # ACTIVOS
        {"codigo": "ACT-CAJA", "nombre": "Caja", "tipo": "ACTIVO", "grupo": None},
        {"codigo": "ACT-BANCOS", "nombre": "Bancos", "tipo": "ACTIVO", "grupo": None},
        {"codigo": "ACT-CXC", "nombre": "Cuentas por cobrar", "tipo": "ACTIVO", "grupo": None},
    ]
    for cat in default_categories:
        stmt = select(categorias.c.codigo).where(categorias.c.codigo == cat["codigo"])
        existing = conn.execute(stmt).first()
        if existing:
            # Actualizar grupo y otros campos
            stmt_upd = (
                update(categorias)
                .where(categorias.c.codigo == cat["codigo"])
                .values(
                    nombre=cat["nombre"],
                    tipo=cat["tipo"],
                    grupo=cat["grupo"],
                    activo=True
                )
            )
            conn.execute(stmt_upd)
        else:
            ins = insert(categorias).values(
                id=uuid4(),
                codigo=cat["codigo"],
                nombre=cat["nombre"],
                tipo=cat["tipo"],
                grupo=cat["grupo"],
                activo=True
            )
            conn.execute(ins)
    # No commit here; managed by outer context manager


def run_initial_migrations(conn):
    """Run all initial migrations in order."""
    migrate_movements_table(conn)
    migrate_categorias_table(conn)
    seed_default_categories(conn)
