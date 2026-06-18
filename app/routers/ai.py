from __future__ import annotations

import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from sqlalchemy.engine import Connection

from app.database import get_connection
from app.core.security import get_current_user
from app.schemas.ai import (
    ParseIncomeRequest,
    ParseIncomeResponse,
    ParseExpenseRequest,
    ParseExpenseResponse,
    ParseTransferRequest,
    ParseTransferResponse,
    ParseCreditRequest,
    ParseCreditResponse,
    ParseAutoRequest,
    ParseAutoResponse,
    AIParseError,
)

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


def get_db() -> Connection:
    with get_connection() as connection:
        yield connection


@router.post("/parse-income")
async def parse_income(
    payload: ParseIncomeRequest,
    request: Request,
    connection: Connection = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Parse natural language text into a structured income movement proposal.

    Returns the raw parsed movement dict and usage stats.
    """
    parser = request.app.state.ai_parser
    logger.info("[AI parse-income] Received text: %s, context length: %d", payload.text, len(payload.context))
    try:
        parsed = await parser.parse_income_text(connection, payload.text, context=payload.context)
        usage = parser.get_usage()
        logger.info("[AI parse-income] Parsed result: %s, usage: %s", parsed, usage)
        return {"movement": parsed, "usage": usage}
    except Exception as e:
        logger.exception("AI parsing error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "parse_error", "detail": str(e)},
        )


@router.post("/parse-expense")
async def parse_expense(
    payload: ParseExpenseRequest,
    request: Request,
    connection: Connection = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Parse natural language text into a structured expense movement."""
    parser = request.app.state.ai_parser
    logger.info("[AI parse-expense] Received text: %s, context length: %d", payload.text, len(payload.context))
    try:
        result = await parser.parse_expense_text(connection, payload.text, context=payload.context)
        usage = parser.get_usage()
        logger.info("[AI parse-expense] Parsed result: %s, usage: %s", result, usage)
        return {"movement": result, "usage": usage}
    except Exception as e:
        logger.exception("AI expense parsing error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "parse_error", "detail": str(e)},
        )


@router.post("/parse-transfer")
async def parse_transfer(
    payload: ParseTransferRequest,
    request: Request,
    connection: Connection = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Parse natural language text into a structured transfer movement."""
    parser = request.app.state.ai_parser
    logger.info("[AI parse-transfer] Received text: %s, context length: %d", payload.text, len(payload.context))
    try:
        result = await parser.parse_transfer_text(connection, payload.text, context=payload.context)
        usage = parser.get_usage()
        logger.info("[AI parse-transfer] Parsed result: %s, usage: %s", result, usage)
        return {"movement": result, "usage": usage}
    except Exception as e:
        logger.exception("AI transfer parsing error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "parse_error", "detail": str(e)},
        )


@router.post("/parse-credit")
async def parse_credit(
    payload: ParseCreditRequest,
    request: Request,
    connection: Connection = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Parse natural language text into a structured credit creation payload."""
    parser = request.app.state.ai_parser
    logger.info("[AI parse-credit] Received text: %s, context length: %d", payload.text, len(payload.context))
    try:
        result = await parser.parse_credit_text(connection, payload.text, context=payload.context)
        usage = parser.get_usage()
        logger.info("[AI parse-credit] Parsed result: %s, usage: %s", result, usage)
        return {"movement": result, "usage": usage}
    except Exception as e:
        logger.exception("AI credit parsing error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "parse_error", "detail": str(e)},
        )


@router.post("/parse")
async def parse_auto(
    payload: ParseAutoRequest,
    request: Request,
    connection: Connection = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Unified endpoint: AI automatically detects movement type (income/expense/transfer/credit) and extracts structured data.

    Returns the movement type, the raw parsed movement dict and usage stats.
    """
    parser = request.app.state.ai_parser
    logger.info("[AI parse-auto] Received text: %s, context length: %d", payload.text, len(payload.context))
    try:
        movement_type, result, usage = await parser.parse_auto(
            connection, payload.text, context=payload.context
        )
        logger.info("[AI parse-auto] Detected type: %s, result: %s, usage: %s", movement_type, result, usage)
        return {
            "movement_type": movement_type,
            "movement": result,
            "usage": usage,
        }
    except Exception as e:
        logger.exception("AI auto parsing error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "parse_error", "detail": str(e)},
        )


@router.get("/health")
async def ai_health(
    _: dict = Depends(get_current_user),
):
    """Health check for AI parser feature."""
    from app.config import AI_PARSER_ENABLED, GROQ_API_KEY

    return {
        "enabled": AI_PARSER_ENABLED,
        "configured": bool(GROQ_API_KEY),
    }


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    duration: float = Form(...),
    request: Request = None,
    connection: Connection = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Transcribe audio file to text using Whisper."""
    whisper_service = request.app.state.whisper_service
    content = await audio.read()
    try:
        text = whisper_service.transcribe(content, audio.filename or "audio.webm", duration)
        usage = whisper_service.get_usage()
        return {"text": text, "usage": usage}
    except Exception as e:
        logger.exception("Whisper transcription error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage")
async def get_usage(
    request: Request,
    _: dict = Depends(get_current_user),
):
    """Get current usage stats for Groq Chat and Whisper."""
    parser = request.app.state.ai_parser
    whisper_service = request.app.state.whisper_service
    chat_usage = parser.get_usage()
    whisper_usage = whisper_service.get_usage()
    print(f"[AI usage] parser_id={id(parser)} chat={chat_usage}")
    print(f"[AI usage] whisper_id={id(whisper_service)} whisper={whisper_usage}")
    logger.info("[AI usage] Returning chat=%s, whisper=%s", chat_usage, whisper_usage)
    return {"chat": chat_usage, "whisper": whisper_usage}
