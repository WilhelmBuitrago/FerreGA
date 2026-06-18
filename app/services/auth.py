from __future__ import annotations

from sqlalchemy.engine import Connection
from sqlalchemy import select, func

from app.core import auth as auth_core
from app.repositories import users as users_repo
from app.models.tables import usuarios


class AuthError(ValueError):
    pass


def authenticate_user(connection: Connection, *, username: str, password: str) -> dict:
    print(f"[DEBUG] authenticate_user: username={username}")
    user = users_repo.get_user_by_id(connection, user_id=username)
    print(f"[DEBUG] user from DB: {user}")
    if not user or not user.get("password_hash"):
        raise AuthError("Invalid credentials")
    if not auth_core.verify_password(password, user["password_hash"]):
        raise AuthError("Invalid credentials")
    return user


def ensure_admin_user(connection: Connection) -> dict:
    """Ensure at least one admin user exists and sync its password with ADMIN_PASSWORD."""
    import os
    import secrets
    import string

    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        # Si no hay ADMIN_PASSWORD, generamos uno aleatorio (solo si vamos a crear o actualizar)
        admin_password = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
        )
        print(f"[WARNING] ADMIN_PASSWORD no definido. Usando contraseña temporal: {admin_password}")
        print("[WARNING] Por favor configura ADMIN_PASSWORD en producción!")

    password_hash = auth_core.hash_password(admin_password)

    # Buscar si ya existe algún usuario con rol admin (case-insensitive)
    stmt = select(usuarios.c.id).where(func.lower(usuarios.c.role) == "admin")
    existing_admin = connection.execute(stmt).first()

    if existing_admin:
        admin_id = existing_admin[0]
        # Actualizar la contraseña del admin existente para que coincida con ADMIN_PASSWORD
        updated = users_repo.update_user_credentials(
            connection,
            user_id=admin_id,
            password_hash=password_hash,
            role="admin",
        )
        # Devolvemos el admin actualizado si está disponible, sino un dict mínimo
        if updated:
            return updated
        user = users_repo.get_user_by_id(connection, user_id=admin_id)
        return user if user else {"id": admin_id, "role": "admin"}

    # No existe admin, lo creamos con user_id='admin' y nombre por defecto
    return users_repo.create_user(
        connection,
        user_id=os.getenv("ADMIN_USER_ID", "admin"),
        name=os.getenv("ADMIN_NAME", "Administrador"),
        password_hash=password_hash,
        role="admin",
    )
