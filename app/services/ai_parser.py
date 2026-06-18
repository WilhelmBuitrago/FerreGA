from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.config import (
    AI_PARSER_ENABLED,
    AI_PARSER_MODE,
    GROQ_API_KEY,
    GROQ_MODEL,
    NVIDIA_API_KEY,
    NVIDIA_MODEL,
    AI_PARSER_PROVIDER,
)
from app.schemas.ai import ParsedIncome
from app.services.ai_providers import GroqProvider, NvidiaProvider
from .ai_parser_base import AIParsingError
from .ai_parser_legacy import AIParserLegacy
from .ai_parser_auto import AIParserAuto

logger = logging.getLogger(__name__)


class AIParser:
    """Orchestrator for AI parsing service with dual fallback: provider + mode."""

    def __init__(self, api_key: str | None = None, mode: str | None = None):
        self.api_key = api_key or GROQ_API_KEY
        self.mode = (mode or AI_PARSER_MODE or "legacy").lower()
        self.provider = self._create_provider()
        self._legacy_parser: AIParserLegacy | None = None
        self._auto_parser: AIParserAuto | None = None
        logger.info(
            f"[AIParser] Initialized with provider: {self.provider.__class__.__name__}, mode: {self.mode}"
        )

    def _create_provider(self):
        provider_type = AI_PARSER_PROVIDER or "nvidia"
        if provider_type.lower() == "groq":
            return GroqProvider(api_key=self.api_key, model=GROQ_MODEL)
        else:
            nvidia_key = NVIDIA_API_KEY or self.api_key
            if not nvidia_key:
                raise AIParsingError("NVIDIA_API_KEY not configured")
            nvidia_model = NVIDIA_MODEL or "stepfun-ai/step-3.7-flash"
            return NvidiaProvider(api_key=nvidia_key, model=nvidia_model)

    def _get_parser(self):
        if self.mode == "auto":
            if self._auto_parser is None:
                self._auto_parser = AIParserAuto(provider=self.provider)
            return self._auto_parser
        else:
            if self._legacy_parser is None:
                self._legacy_parser = AIParserLegacy(provider=self.provider)
            return self._legacy_parser

    async def parse_income_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> ParsedIncome:
        if not AI_PARSER_ENABLED:
            raise AIParsingError("AI parser is disabled")
        try:
            parser = self._get_parser()
            result = await parser.parse_income_text(connection, text, context)
            if isinstance(result, dict):
                return result
            if isinstance(result, ParsedIncome):
                return result
            raise AIParsingError(f"Unexpected parsed income type: {type(result)}")
        except AIParsingError as e:
            if "account_id" in str(e).lower() or "categoria_codigo" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "invalid_movement_type", "detail": str(e)},
                )
            # Error de parsing/tools (fallback a legacy con mismo proveedor)
            if self.mode == "auto":
                logger.warning(
                    f"Auto parsing error (tools) ({e}), falling back to legacy with same provider"
                )
                legacy = AIParserLegacy(provider=self.provider)
                return await legacy.parse_income_text(connection, text, context)
            raise
        except Exception as e:
            # Error de red/proveedor
            if self.mode == "auto" and isinstance(self.provider, NvidiaProvider):
                logger.warning(
                    f"NVIDIA provider error (network/response) ({e}), switching to Groq auto"
                )
                groq_provider = GroqProvider(api_key=GROQ_API_KEY, model=GROQ_MODEL)
                auto_parser = AIParserAuto(provider=groq_provider)
                try:
                    result = await auto_parser.parse_income_text(
                        connection, text, context
                    )
                    if isinstance(result, dict):
                        return result
                    if isinstance(result, ParsedIncome):
                        return result
                    raise AIParsingError(
                        f"Unexpected parsed income type: {type(result)}"
                    )
                except AIParsingError as e2:
                    # Groq auto falló por tools → legacy con Groq
                    logger.warning(
                        f"Groq auto parsing error ({e2}), falling back to Groq legacy"
                    )
                    legacy = AIParserLegacy(provider=groq_provider)
                    return await legacy.parse_income_text(connection, text, context)
                except Exception as e2:
                    # Groq auto falló por red también
                    raise AIParsingError(
                        f"Both providers failed: primary={e}, fallback={e2}"
                    ) from e2
            else:
                raise

    async def parse_expense_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        if not AI_PARSER_ENABLED:
            raise AIParsingError("AI parser is disabled")
        try:
            parser = self._get_parser()
            return await parser.parse_expense_text(connection, text, context)
        except AIParsingError as e:
            if self.mode == "auto":
                logger.warning(
                    f"Auto parsing error (tools) ({e}), falling back to legacy with same provider"
                )
                legacy = AIParserLegacy(provider=self.provider)
                return await legacy.parse_expense_text(connection, text, context)
            raise
        except Exception as e:
            if self.mode == "auto" and isinstance(self.provider, NvidiaProvider):
                logger.warning(
                    f"NVIDIA provider error (network/response) ({e}), switching to Groq auto"
                )
                groq_provider = GroqProvider(api_key=GROQ_API_KEY, model=GROQ_MODEL)
                auto_parser = AIParserAuto(provider=groq_provider)
                try:
                    return await auto_parser.parse_expense_text(
                        connection, text, context
                    )
                except AIParsingError as e2:
                    logger.warning(
                        f"Groq auto parsing error ({e2}), falling back to Groq legacy"
                    )
                    legacy = AIParserLegacy(provider=groq_provider)
                    return await legacy.parse_expense_text(connection, text, context)
                except Exception as e2:
                    raise AIParsingError(
                        f"Both providers failed: primary={e}, fallback={e2}"
                    ) from e2
            else:
                raise

    async def parse_transfer_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        if not AI_PARSER_ENABLED:
            raise AIParsingError("AI parser is disabled")
        try:
            parser = self._get_parser()
            return await parser.parse_transfer_text(connection, text, context)
        except AIParsingError as e:
            if self.mode == "auto":
                logger.warning(
                    f"Auto parsing error (tools) ({e}), falling back to legacy with same provider"
                )
                legacy = AIParserLegacy(provider=self.provider)
                return await legacy.parse_transfer_text(connection, text, context)
            raise
        except Exception as e:
            if self.mode == "auto" and isinstance(self.provider, NvidiaProvider):
                logger.warning(
                    f"NVIDIA provider error (network/response) ({e}), switching to Groq auto"
                )
                groq_provider = GroqProvider(api_key=GROQ_API_KEY, model=GROQ_MODEL)
                auto_parser = AIParserAuto(provider=groq_provider)
                try:
                    return await auto_parser.parse_transfer_text(
                        connection, text, context
                    )
                except AIParsingError as e2:
                    logger.warning(
                        f"Groq auto parsing error ({e2}), falling back to Groq legacy"
                    )
                    legacy = AIParserLegacy(provider=groq_provider)
                    return await legacy.parse_transfer_text(connection, text, context)
                except Exception as e2:
                    raise AIParsingError(
                        f"Both providers failed: primary={e}, fallback={e2}"
                    ) from e2
            else:
                raise

    async def parse_credit_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        if not AI_PARSER_ENABLED:
            raise AIParsingError("AI parser is disabled")
        try:
            parser = self._get_parser()
            result = await parser.parse_credit_text(connection, text, context)
            return result
        except AIParsingError as e:
            if self.mode == "auto":
                logger.warning(
                    f"Auto parsing error (tools) ({e}), falling back to legacy with same provider"
                )
                legacy = AIParserLegacy(provider=self.provider)
                return await legacy.parse_credit_text(connection, text, context)
            raise
        except Exception as e:
            if self.mode == "auto" and isinstance(self.provider, NvidiaProvider):
                logger.warning(
                    f"NVIDIA provider error (network/response) ({e}), switching to Groq auto"
                )
                groq_provider = GroqProvider(api_key=GROQ_API_KEY, model=GROQ_MODEL)
                auto_parser = AIParserAuto(provider=groq_provider)
                try:
                    return await auto_parser.parse_credit_text(
                        connection, text, context
                    )
                except AIParsingError as e2:
                    logger.warning(
                        f"Groq auto parsing error ({e2}), falling back to Groq legacy"
                    )
                    legacy = AIParserLegacy(provider=groq_provider)
                    return await legacy.parse_credit_text(connection, text, context)
                except Exception as e2:
                    raise AIParsingError(
                        f"Both providers failed: primary={e}, fallback={e2}"
                    ) from e2
            else:
                raise

    async def parse_auto(
        self, connection, text: str, context: list[dict] | None = None
    ) -> tuple[str, dict, dict]:
        if not AI_PARSER_ENABLED:
            raise AIParsingError("AI parser is disabled")
        # Force auto parser regardless of mode
        parser = AIParserAuto(provider=self.provider)
        result = await parser.parse_auto(connection, text, context)
        usage = self.provider.get_usage()
        if not isinstance(result, dict):
            raise AIParsingError("Auto parser did not return a dict")
        movement_type = result.pop("movement_type", "unknown")
        return movement_type, result, usage

    def get_usage(self) -> dict:
        return self.provider.get_usage()
