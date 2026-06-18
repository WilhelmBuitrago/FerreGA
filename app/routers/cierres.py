from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.schemas import CierreCreate, CierreOut
from app.services import cierres as cierre_service

router = APIRouter(prefix="/api/cierres", tags=["cierres"])


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


def _service_error_to_http(exc: cierre_service.CierreDuplicadoError | cierre_service.CierreValidationError | cierre_service.CierreLockedError) -> HTTPException:
    code: str = getattr(exc, "error_code", "unknown")
    status_map: dict[str, int] = {
        "validation": 400,
        "duplicate": 409,
        "locked": 409,
    }
    return HTTPException(
        status_code=status_map.get(code, 500),
        detail={"error": code, "message": str(exc)},
    )


@router.post(
    "/close",
    response_model=CierreOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cierre de turno",
    description="Registra el cierre de turno y bloquea edicion del cierre.",
)
def registrar_cierre(
    payload: CierreCreate,
    response: Response,
    connection: Connection = Depends(get_db),
):
    try:
        cierre, created = cierre_service.registrar_cierre(
            connection,
            turno_id=payload.turno_id,
            monto_cierre=payload.monto_cierre,
            notas=payload.notas,
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return cierre
    except (
        cierre_service.CierreDuplicadoError,
        cierre_service.CierreValidationError,
    ) as exc:
        raise _service_error_to_http(exc) from exc


@router.get(
    "",
    response_model=list[CierreOut],
    summary="Listar cierres",
    description="Lista cierres activos.",
)
def list_cierres(connection: Connection = Depends(get_db)):
    return cierre_service.list_cierres(connection)


@router.get(
    "/{cierre_id}",
    response_model=CierreOut,
    summary="Detalle de cierre",
    description="Obtiene el detalle de un cierre.",
)
def get_cierre(cierre_id: UUID, connection: Connection = Depends(get_db)):
    try:
        return cierre_service.get_cierre(connection, cierre_id=cierre_id)
    except cierre_service.CierreLockedError as exc:
        raise _service_error_to_http(exc) from exc