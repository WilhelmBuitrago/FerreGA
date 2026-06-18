from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path cuando se ejecuta python app/main.py
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configurar logging para desarrollo
import logging
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
logging.getLogger("app.services.ai_parser").setLevel(logging.DEBUG)

print("[DEBUG] Intentando importar routers...")
try:
    from app.routers import (
        accounts_router,
        ai_router,
        auth_router,
        categories_router,
        credits_router,
        movements_router,
        sync_router,
        turns_router,
        admin as admin_router,
    )
    print("[DEBUG] Routers importados correctamente")
    print(f"[DEBUG] accounts_router.routes: {len(accounts_router.routes)}")
    print(f"[DEBUG] categories_router.routes: {len(categories_router.routes)}")
    print(f"[DEBUG] movements_router.routes: {len(movements_router.routes)}")
    print(f"[DEBUG] turns_router.routes: {len(turns_router.routes)}")
    print(f"[DEBUG] ai_router.routes: {len(ai_router.routes)}")
    print(f"[DEBUG] auth_router.routes: {len(auth_router.routes)}")
    print(f"[DEBUG] credits_router.routes: {len(credits_router.routes)}")
    print(f"[DEBUG] sync_router.routes: {len(sync_router.routes)}")
    print(f"[DEBUG] admin_router.router.routes: {len(admin_router.router.routes)}")
except Exception as e:
    print(f"[ERROR] Falló importación de routers: {e}")
    raise
from app.core.error_handling import register_error_handlers
from app.models.tables import metadata
from app.database import engine, get_connection
from app.services import auth as auth_service
from app.migrations.initial import run_initial_migrations


metadata.create_all(engine)
with get_connection() as connection:
    run_initial_migrations(connection)
    auth_service.ensure_admin_user(connection)

app = FastAPI(title="FerreGA Caja API", version="0.1.0")
register_error_handlers(app)

# Inicializar servicios AI y adjuntarlos al estado de la app (persist while app lives)
from app.services.ai_parser import AIParser
from app.services.whisper_service import WhisperService

app.state.ai_parser = AIParser()
app.state.whisper_service = WhisperService()

# CORS configurable through environment (comma-separated). Default: localhost dev server.
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers ANTES de montar archivos estáticos
app.include_router(accounts_router)
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(turns_router)
app.include_router(credits_router)
app.include_router(movements_router)
app.include_router(sync_router)
app.include_router(admin_router.router)
print(f"[DEBUG] Admin routes: {[r.path for r in admin_router.router.routes]}", flush=True)

# Servir frontend estático en producción (después de los routers)
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

# DEBUG: Listar rutas registradas (solo APIRoute, ignorando Mount)
from fastapi.routing import APIRoute
print("=== RUTAS REGISTRADAS ===")
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"{route.path} {list(route.methods)}")
print("==========================")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
