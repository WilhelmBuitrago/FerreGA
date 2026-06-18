from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

from pydantic import ValidationError

from app.models.tables import accounts, categorias, credits
from app.schemas.ai import ParsedIncome

logger = logging.getLogger(__name__)

class AIParsingError(ValueError):
    """Raised when AI parsing fails or returns invalid data."""
    pass

class AIParserBase:
    """Base class for AI parsing service with shared infrastructure. Uses a Provider for LLM calls."""

    # Common tool schema for AUTO mode (new design with intent + dynamic context)
    TOOLS_SCHEMA = [
        {
            "type": "function",
            "function": {
                "name": "intent",
                "description": "Especifica la intención del usuario para el movimiento. Llamar ESTA herramienta siempre que inicies o detectes un CAMBIO en la intención.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo": {
                            "type": "string",
                            "enum": ["ingreso", "egreso", "transferencia", "credito"],
                            "description": "Tipo de movimiento: ingreso, egreso, transferencia o credito"
                        }
                    },
                    "required": ["tipo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "crear_ingreso",
                "description": "Crea un movimiento de ingreso. Requiere: cuenta (nombre exacto), monto (número positivo), categoria_codigo (código exacto). Descripción es opcional.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuenta": {"type": "string", "description": "Nombre exacto de la cuenta de ingreso"},
                        "monto": {"type": "number", "description": "Monto del ingreso (debe ser positivo)"},
                        "categoria_codigo": {"type": "string", "description": "Código exacto de la categoría de ingreso"},
                        "descripcion": {"type": "string", "description": "Descripción opcional del ingreso"}
                    },
                    "required": ["cuenta", "monto", "categoria_codigo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "crear_egreso",
                "description": "Crea un movimiento de egreso. Requiere: cuenta (nombre exacto), monto (número positivo), categoria_codigo (código exacto). Descripción es opcional.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuenta": {"type": "string", "description": "Nombre exacto de la cuenta de egreso"},
                        "monto": {"type": "number", "description": "Monto del egreso (debe ser positivo)"},
                        "categoria_codigo": {"type": "string", "description": "Código exacto de la categoría de egreso"},
                        "descripcion": {"type": "string", "description": "Descripción opcional del egreso"}
                    },
                    "required": ["cuenta", "monto", "categoria_codigo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "crear_transferencia",
                "description": "Crea una transferencia entre dos cuentas. Requiere: cuenta_origen (nombre exacto), cuenta_destino (nombre exacto), monto (número positivo). Descripción es opcional.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuenta_origen": {"type": "string", "description": "Nombre exacto de la cuenta de origen"},
                        "cuenta_destino": {"type": "string", "description": "Nombre exacto de la cuenta de destino"},
                        "monto": {"type": "number", "description": "Monto a transferir (debe ser positivo)"},
                        "descripcion": {"type": "string", "description": "Descripción opcional de la transferencia"}
                    },
                    "required": ["cuenta_origen", "cuenta_destino", "monto"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "crear_credito",
                "description": "Crea un nuevo crédito (venta a crédito o compra a crédito). Requiere: tipo_credito (CREDIT_SALE o CREDIT_PURCHASE), monto, fecha_vencimiento (YYYY-MM-DD). Descripción es opcional.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_credito": {
                            "type": "string",
                            "enum": ["CREDIT_SALE", "CREDIT_PURCHASE"],
                            "description": "Tipo de crédito: CREDIT_SALE (venta a crédito, CxC) o CREDIT_PURCHASE (compra a crédito, CxP)"
                        },
                        "monto": {"type": "number", "description": "Monto total del crédito (debe ser positivo)"},
                        "fecha_vencimiento": {"type": "string", "format": "date", "description": "Fecha de vencimiento en formato YYYY-MM-DD"},
                        "descripcion": {"type": "string", "description": "Descripción opcional del crédito"}
                    },
                    "required": ["tipo_credito", "monto", "fecha_vencimiento"],
                },
            },
        },
    ]

    def __init__(self, provider: Any):
        """Initialize with a Provider instance."""
        self.provider = provider

    @staticmethod
    def _clean_json_markdown(content: str) -> str:
        """Remove markdown code fences if present (```json ... ```)."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            else:
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        return cleaned

    # Database access methods (shared)
    def _list_accounts(self, connection) -> list[str]:
        """Get list of active account names for prompt context."""
        from sqlalchemy import select
        stmt = select(accounts.c.name).where(accounts.c.is_active.is_(True))
        result = connection.execute(stmt)
        return [row.name for row in result.mappings()]

    def _list_income_categories(self, connection) -> list[dict[str, str]]:
        """Get list of active income categories (codigo, nombre) for prompt context."""
        from sqlalchemy import select
        stmt = select(
            categorias.c.codigo,
            categorias.c.nombre,
        ).where(
            categorias.c.activo.is_(True),
            categorias.c.tipo == "INGRESO",
        )
        result = connection.execute(stmt)
        return [{"codigo": row.codigo, "nombre": row.nombre} for row in result.mappings()]

    def _list_expense_categories(self, connection) -> list[dict[str, str]]:
        """Get list of active expense categories (codigo, nombre)."""
        from sqlalchemy import select
        stmt = select(
            categorias.c.codigo,
            categorias.c.nombre,
        ).where(
            categorias.c.activo.is_(True),
            categorias.c.tipo == "GASTO",
        )
        result = connection.execute(stmt)
        return [{"codigo": row.codigo, "nombre": row.nombre} for row in result.mappings()]

    def _list_credits(self, connection) -> list[dict]:
        """List pending or partial credits for payment selection."""
        from sqlalchemy import select
        stmt = select(
            credits.c.id,
            credits.c.type,
            credits.c.total_amount,
            credits.c.due_date,
            credits.c.description,
            credits.c.status,
        ).where(credits.c.status.in_(["PENDIENTE", "PARCIAL"]))
        result = connection.execute(stmt)
        rows = []
        for row in result.mappings():
            rows.append({
                "id": str(row.id),
                "type": row.type,
                "total_amount": str(row.total_amount) if row.total_amount is not None else None,
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "description": row.description,
                "status": row.status,
            })
        return rows

    def _resolve_account_entity(self, connection, account_name: str) -> dict | None:
        """Resolve account name to account entity (case-insensitive)."""
        from sqlalchemy import func, select
        normalized_name = account_name.strip().lower()
        stmt = select(
            accounts.c.id,
            accounts.c.name,
        ).where(func.lower(accounts.c.name) == normalized_name)
        result = connection.execute(stmt)
        return result.mappings().one_or_none()

    def _resolve_category_codigo(
        self, connection, category_codigo: str, tipo: str | None = None
    ) -> str | None:
        """Validate that category codigo exists and is active (case-insensitive). Optionally filter by tipo (INGRESO/EGRESO)."""
        from sqlalchemy import func, select
        normalized_code = category_codigo.strip().lower()
        stmt = select(categorias.c.codigo).where(
            func.lower(categorias.c.codigo) == normalized_code,
            categorias.c.activo.is_(True),
        )
        if tipo:
            stmt = stmt.where(categorias.c.tipo == tipo)
        result = connection.execute(stmt)
        row = result.mappings().one_or_none()
        return row["codigo"] if row else None

    # Tool execution methods for AUTO mode (used by AIParserAuto)
    def _listar_cuentas(self, connection) -> list[str]:
        """Tool: listar_cuentas - returns active account names."""
        return self._list_accounts(connection)

    def _listar_categorias(self, connection, tipo: str) -> list[dict]:
        """Tool: listar_categorias - returns categories based on tipo ('ingreso' or 'egreso')."""
        if tipo.lower() == "ingreso":
            return self._list_income_categories(connection)
        elif tipo.lower() == "egreso":
            return self._list_expense_categories(connection)
        else:
            raise AIParsingError(f"Tipo inválido para categorías: {tipo}. Use 'ingreso' o 'egreso'.")

    def _crear_ingreso(self, connection, cuenta: str, monto: float, categoria_codigo: str, descripcion: str | None = None) -> dict:
        """Tool: crear_ingreso - resolves account and category, validates, returns the payload dict."""
        account_entity = self._resolve_account_entity(connection, cuenta)
        if not account_entity:
            raise AIParsingError(f"Cuenta '{cuenta}' no encontrada")
        try:
            amount = Decimal(str(monto))
        except Exception:
            raise AIParsingError(f"Monto inválido: {monto}")
        if amount <= 0:
            raise AIParsingError("El monto debe ser positivo")
        resolved_codigo = self._resolve_category_codigo(connection, categoria_codigo, tipo="INGRESO")
        if not resolved_codigo:
            raise AIParsingError(f"Categoría de ingreso '{categoria_codigo}' no encontrada")
        return {
            "account_id": account_entity["id"],
            "amount": amount,
            "categoria_codigo": resolved_codigo,
            "description": descripcion,
        }

    def _crear_egreso(self, connection, cuenta: str, monto: float, categoria_codigo: str, descripcion: str | None = None) -> dict:
        """Tool: crear_egreso - resolves account and category, validates, returns the payload dict."""
        account_entity = self._resolve_account_entity(connection, cuenta)
        if not account_entity:
            raise AIParsingError(f"Cuenta '{cuenta}' no encontrada")
        try:
            amount = Decimal(str(monto))
        except Exception:
            raise AIParsingError(f"Monto inválido: {monto}")
        if amount <= 0:
            raise AIParsingError("El monto debe ser positivo")
        resolved_codigo = self._resolve_category_codigo(connection, categoria_codigo, tipo="GASTO")
        if not resolved_codigo:
            raise AIParsingError(f"Categoría de egreso '{categoria_codigo}' no encontrada")
        return {
            "account_id": account_entity["id"],
            "amount": amount,
            "categoria_codigo": resolved_codigo,
            "description": descripcion,
        }

    def _crear_transferencia(self, connection, cuenta_origen: str, cuenta_destino: str, monto: float, descripcion: str | None = None) -> dict:
        """Tool: crear_transferencia - resolves both accounts, validates, returns payload dict."""
        if cuenta_origen == cuenta_destino:
            raise AIParsingError("Las cuentas de origen y destino deben ser diferentes")
        source_entity = self._resolve_account_entity(connection, cuenta_origen)
        if not source_entity:
            raise AIParsingError(f"Cuenta de origen '{cuenta_origen}' no encontrada")
        target_entity = self._resolve_account_entity(connection, cuenta_destino)
        if not target_entity:
            raise AIParsingError(f"Cuenta de destino '{cuenta_destino}' no encontrada")
        try:
            amount = Decimal(str(monto))
        except Exception:
            raise AIParsingError(f"Monto inválido: {monto}")
        if amount <= 0:
            raise AIParsingError("El monto debe ser positivo")
        return {
            "source_account_id": source_entity["id"],
            "target_account_id": target_entity["id"],
            "amount": amount,
            "description": descripcion,
        }

    def _crear_credito(self, connection, tipo_credito: str, monto: float, fecha_vencimiento: str, descripcion: str | None = None) -> dict:
        """Tool: crear_credito - validates credit type, amount, date, returns payload dict."""
        type_mapping = {
            "CXC": "CREDIT_SALE",
            "CXP": "CREDIT_PURCHASE",
            "CREDIT_SALE": "CREDIT_SALE",
            "CREDIT_PURCHASE": "CREDIT_PURCHASE",
            "VENTA_CREDITO": "CREDIT_SALE",
            "COMPRA_CREDITO": "CREDIT_PURCHASE",
        }
        normalized_type = type_mapping.get(str(tipo_credito).upper())
        if not normalized_type:
            raise AIParsingError(f"Tipo de crédito inválido: {tipo_credito}. Use: CXC, CXP, CREDIT_SALE, CREDIT_PURCHASE")
        try:
            total_amount = Decimal(str(monto))
        except Exception:
            raise AIParsingError(f"Monto inválido: {monto}")
        if total_amount <= 0:
            raise AIParsingError("El monto debe ser positivo")
        try:
            due_date = datetime.fromisoformat(fecha_vencimiento.replace("Z", "+00:00"))
        except Exception as e:
            raise AIParsingError(f"Fecha de vencimiento inválida: {fecha_vencimiento}") from e
        return {
            "type": normalized_type,
            "total_amount": total_amount,
            "due_date": due_date,
            "description": descripcion,
        }

    # Context normalization
    async def _normalize_context(self, context: list[dict] | None) -> list[dict]:
        if not context:
            return []
        normalized = []
        for msg in context:
            if isinstance(msg, dict):
                normalized.append(msg)
            else:
                normalized.append({
                    "role": getattr(msg, "role", "user"),
                    "content": getattr(msg, "content", None) or ""
                })
        return normalized

    # Get usage from provider
    def get_usage(self):
        """Return usage from the underlying provider."""
        return self.provider.get_usage()
