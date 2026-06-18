from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.types import uuid7

logger = logging.getLogger("ferrega.error_handling")

REQUEST_ID_HEADER = "X-Request-ID"

# Analytics logger for metrics
analytics_logger = logging.getLogger("ferrega.analytics")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        error = _status_to_error(exc.status_code)
        request_id = _get_request_id(request)

        logger.warning(
            "HTTP %d | %s %s | request_id=%s | detail=%s",
            exc.status_code,
            request.method,
            request.url.path,
            request_id,
            exc.detail,
        )

        details = None
        message = str(exc.detail)
        if isinstance(exc.detail, dict):
            error = str(exc.detail.get("error") or exc.detail.get("code") or error)
            message = str(exc.detail.get("message") or message)
            details = exc.detail.get("details")
        elif isinstance(exc.detail, list):
            message = str(exc.detail)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error,
                "message": message,
                **({"details": details} if details is not None else {}),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        details = _extract_validation_details(exc)

        logger.warning(
            "Validation error | %s %s | request_id=%s | errors=%d",
            request.method,
            request.url.path,
            request_id,
            len(details),
        )

        return JSONResponse(
            status_code=400,
            content={
                "error": "validation",
                "message": "Invalid request payload",
                "details": details,
            },
        )

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid7())
        request.state.request_id = request_id  # type: ignore[attr-defined]

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @app.middleware("http")
    async def analytics_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Log request metrics for analytics (4xx client errors)."""
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log metrics for client errors (4xx)
        if 400 <= response.status_code < 500:
            analytics_logger.info(
                "client_error | %s %s | status=%d | duration=%.1fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        return response


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")  # type: ignore[attr-defined]


def _status_to_error(status: int) -> str:
    if status == 400:
        return "validation"
    if status == 404:
        return "not_found"
    if status == 409:
        return "conflict"
    return "http"


def _extract_validation_details(exc: RequestValidationError) -> list[dict]:
    details: list[dict] = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field = "body" if not loc else str(loc[-1])
        details.append(
            {
                "field": field,
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error"),
            }
        )
    return details
