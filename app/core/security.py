from __future__ import annotations

import json
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select

from app.core import auth as auth_core
from app.database import get_connection
from app.models.tables import cierres
from app.repositories import users as users_repo

security_scheme = HTTPBearer(auto_error=False)


async def detect_cierre_duplicado(request: Request, call_next):
    if request.url.path == "/api/cierres/close" and request.method == "POST":
        body = await request.body()
        request._body = body
        payload = json.loads(body) if body else {}
        usuario_id = payload.get("turno_id")
        if usuario_id:
            with get_connection() as connection:
                result = connection.execute(
                    select(cierres.c.id).where(
                        cierres.c.usuario_id == usuario_id,
                        func.date(cierres.c.fecha) == datetime.utcnow().date(),
                        cierres.c.is_active.is_(True),
                    )
                )
                if result.first():
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "duplicate", "message": "Cierre duplicado"},
                    )
    return await call_next(request)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict | None:
    if credentials is None:
        return None
    token = credentials.credentials
    token_data = auth_core.verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    with get_connection() as connection:
        user = users_repo.get_user_by_id(connection, user_id=token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return {
        "id": user["id"],
        "role": user["role"],
        "name": user["nombre"],
    }


def require_admin(user: dict | None = Depends(get_current_user)) -> dict:
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin required"
        )
    return user
