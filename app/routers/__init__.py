"""FastAPI routers."""

from app.routers.accounts import router as accounts_router
from app.routers.ai import router as ai_router
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.credits import router as credits_router
from app.routers.movements import router as movements_router
from app.routers.sync import router as sync_router
from app.routers.turns import router as turns_router

__all__ = [
    "accounts_router",
    "ai_router",
    "auth_router",
    "categories_router",
    "credits_router",
    "movements_router",
    "sync_router",
    "turns_router",
]