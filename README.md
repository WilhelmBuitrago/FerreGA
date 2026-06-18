# FerreGA - MVP Caja (Fases 1-6)

![FerreGA Logo](docs/assets/logo.png)

Sistema de gestion de caja para ferreterias. Gestiona cuentas, turnos y movimientos con sync offline.

## Quick Start

1. **Backend**: `uvicorn app.main:app --reload`
2. **Frontend**: `npm run dev` (en `frontend/`)
3. **API Docs**: http://localhost:8000/docs

## Documentation

- [Guía de Usuario](docs/user-guide.md) - Flujos de trabajo paso a paso
- [Guía de Despliegue](docs/deployment.md) - Configuración de Docker, variables de entorno
- [Lista de Verificación de Release](docs/release-checklist.md) - Pre-flight check list

## Dominio

- **Account**: identificada por UUID, con `name`.
- **Turn**: apertura/cierre con `start_amount`, `end_amount`, `status`.
- **Movement**: ingreso, egreso o transferencia con `amount > 0`.
- **Source of truth**: calculos financieros solo en backend.

## API

### Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/accounts` | Listar cuentas |
| POST | `/accounts` | Crear cuenta |
| GET | `/accounts/{id}` | Detalle de cuenta |
| DELETE | `/accounts/{id}` | Eliminar cuenta |
| POST | `/turns/open` | Abrir turno |
| PATCH | `/turns/{id}/close` | Cerrar turno |
| GET | `/turns/active` | Obtener turno activo |
| POST | `/movements/income` | Agregar ingreso |
| POST | `/movements/expense` | Agregar egreso |
| POST | `/movements/transfer` | Transferencia |
| POST | `/sync` | Sincronizar comandos offline |

## Setup (Developer)

1. Crear entorno virtual y dependencias principales:
   - fastapi
   - uvicorn
   - sqlalchemy
   - psycopg2

2. Configurar variables de entorno en `.env`:
   - `DATABASE_URL` (opcional, default SQLite en `data/ferrega.db`)
   - `APP_SECRET` (opcional)
   - `AUTH_SECRET_KEY` (**requerido** en producción, default desarrollo inseguro)
   - `AUTH_PASSWORD_PEPPER` (**requerido** en producción, default desarrollo inseguro)
   - `ADMIN_PASSWORD` (opcional, si no se provee se genera uno aleatorio la primera vez)
   - `ALLOWED_ORIGINS` (opcional, lista separada por comas de CORS, default `http://localhost:5173`)

3. Iniciar API:
   - `uvicorn app.main:app --reload`

4. Frontend (Vite):
   - `npm install`
   - `npm run dev`

## Testing

- Backend: pytest sobre `tests/`
- Frontend: `npm test`
- E2E: Cypress (ver `frontend/cypress/`)

## Project Structure

```
app/
  core/          # Cross-cutting concerns: auth, security, error handling
  database.py    # Engine factory and connection context manager
  main.py        # FastAPI application entrypoint, middleware, routers
  migrations/    # Database migration scripts (initial)
  models/        # SQLAlchemy table definitions (metadata)
  repositories/  # Data access layer (pure SQLAlchemy)
  routers/       # API endpoint definitions (FastAPI routers)
  schemas/       # Pydantic models for request/response validation
  services/      # Business logic layer (use repositories)
  config.py      # Configuration from environment variables
tests/           # Unit, repository, service, and API tests
frontend/        # TypeScript/React/Vite single-page application
docs/            # User and developer documentation
data/            # SQLite database file (development, gitignored)
```

## Deployment

- Set `DATABASE_URL` (PostgreSQL recommended).
- Set `AUTH_SECRET_KEY` and `AUTH_PASSWORD_PEPPER` (required in prod).
- Optionally set `ADMIN_PASSWORD` for admin endpoints.
- Run application: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- Build frontend: `npm run build` (artifacts in `frontend/dist`), served automatically by FastAPI if present.

## OpenAPI

The API documentation is available at `/docs` (Swagger UI) and `/openapi.json`.
