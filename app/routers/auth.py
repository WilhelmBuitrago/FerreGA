from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from app.core import auth as auth_core
from app.core.security import get_current_user
from app.database import get_connection
from app.schemas import auth as auth_schemas
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.post("/login", response_model=auth_schemas.LoginResponse)
def login(payload: auth_schemas.LoginRequest, connection: Connection = Depends(get_db)):
    try:
        user = auth_service.authenticate_user(
            connection, username=payload.username, password=payload.password
        )
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    token = auth_core.create_token(user_id=user["id"], role=user["role"])
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Devuelve el usuario autenticado actual."""
    return current_user
