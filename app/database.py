from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto (un nivel arriba de app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine


def build_engine(database_url: str | None = None) -> Engine:
    if database_url is not None:
        url = database_url
    else:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            url = env_url
        else:
            # Usar SQLite con ruta absoluta en el proyecto para persistencia
            data_dir = PROJECT_ROOT / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "ferrega.db"
            url = f"sqlite:///{db_path}"
    return create_engine(url, future=True)


engine = build_engine()


@contextmanager
def get_connection() -> Iterator[Connection]:
    with engine.begin() as connection:
        yield connection
