"""
Legacy AI parser mode - UNIFIED system prompt with all information embedded.
No tool calls, all data (accounts, categories, credit types) in one prompt.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from app.schemas.ai import ParsedIncome
from .ai_parser_base import AIParserBase, AIParsingError

logger = logging.getLogger(__name__)


class AIParserLegacy(AIParserBase):
    """Legacy parser implementation - unified system prompt with all context, no tool usage."""

    SYSTEM_PROMPT_LEGACY_UNIFIED = """Eres un asistente experto en contabilidad y finanzas para registrar movimientos financieros. Tu trabajo es analizar el texto del usuario y generar JSON válido para el tipo de movimiento correcto.

# DATOS DEL SISTEMA

## Cuentas activas
{accounts_str}

## Categorías de ingreso (código - nombre)
{income_cats_str}

## Categorías de egreso (código - nombre)
{expense_cats_str}

## Tipos de crédito
- CREDIT_SALE (CxC): Venta a crédito, cuando el cliente paga después
- CREDIT_PURCHASE (CxP): Compra a crédito, cuando tú pagas después

# REGLAS DURAS (OBLIGATORIAS)

1. **Identifica el tipo de movimiento** a partir del texto:
   - **income**: entradas de dinero (ingresos, ventas, pagos recibidos)
   - **expense**: salidas de dinero (gastos, compras, pagos realizados)
   - **transfer**: movimiento entre cuentas propias (mover dinero de una cuenta a otra)
   - **credit_create**: crear un nuevo crédito (venta a crédito o compra a crédito)

2. **Para INGRESOS** (`movement_type: "income"`):
   - `account`: nombre EXACTO de la cuenta (de la lista)
   - `amount`: número positivo (puede incluir símbolos como $)
   - `category`: código EXACTO de categoría de ingreso (de la lista)
   - `description`: texto explicativo OPCIONAL
   - **NO uses categorías de egreso para ingresos**

3. **Para EGRESOS** (`movement_type: "expense"`):
   - `account`: nombre EXACTO de la cuenta
   - `amount`: número positivo
   - `category`: código EXACTO de categoría de egreso
   - `description`: OPCIONAL
   - **NO uses categorías de ingreso para egresos**

4. **Para TRANSFERENCIAS** (`movement_type: "transfer"`):
   - `source_account`: cuenta de origen (EXACTA)
   - `target_account`: cuenta de destino (EXACTA)
   - `amount`: número positivo
   - `description`: OPCIONAL
   - Origen y destino deben ser DIFERENTES

5. **Para CRÉDITOS** (`movement_type: "credit_create"`):
   - `type`: "CREDIT_SALE" (venta a crédito) o "CREDIT_PURCHASE" (compra a crédito)
   - `total_amount`: número positivo
   - `due_date`: fecha en formato YYYY-MM-DD (inferir si es necesario)
   - `description`: OPCIONAL

6. **Prohibido**:
   - Inventar datos si no hay coincidencia exacta
   - Modificar nombres de cuentas o códigos de categoría
   - Dejar campos requeridos vacíos
   - Usar montos negativos o cero

# EJEMPLOS POSITIVOS

## Ingresos
- "Registro una venta de 50000 en banco" → {"movement_type":"income","account":"banco","amount":50000,"category":"ING-VENTAS-CTO"}
- "Recibí pago de 200000 por cuenta corriente" → {"movement_type":"income","account":"cuenta corriente","amount":200000,"category":"ING-OTROS","description":"pago recibido"}
- "Ingreso por servicios de transporte 150000 a nequi" → {"movement_type":"income","account":"nequi","amount":150000,"category":"ING-TRANSPORTE"}

## Egresos
- "Pagué arriendo 300000 desde banco" → {"movement_type":"expense","account":"banco","amount":300000,"category":"GAS-OPER-ARREN"}
- "Compra de mercancía 800000 en caja" → {"movement_type":"expense","account":"caja","amount":800000,"category":"GAS-COMPRA-MERC"}
- "Gasto por nómina 1200000 a bancos" → {"movement_type":"expense","account":"bancos","amount":1200000,"category":"GAS-OPER-NOMINA"}

## Transferencias
- "Transferir 100000 de caja a banco" → {"movement_type":"transfer","source_account":"caja","target_account":"banco","amount":100000}
- "Mueve 50000 del banco a ahorros" → {"movement_type":"transfer","source_account":"banco","target_account":"ahorros","amount":50000}

## Créditos
- "Crear crédito de venta por 500000 con vencimiento 2025-12-31" → {"movement_type":"credit_create","type":"CREDIT_SALE","total_amount":500000,"due_date":"2025-12-31"}
- "Registrar compra a crédito por 200000 el 31-01-2026" → {"movement_type":"credit_create","type":"CREDIT_PURCHASE","total_amount":200000,"due_date":"2026-01-31"}

# EJEMPLOS NEGATIVOS (LO QUE NO DEBES HACER)

- ❌ NO mezcles tipos: un ingreso NO debe usar categoría de egreso
- ❌ NO uses nombres de cuenta diferentes a la lista exacta
- ❌ NO inventes categorías si no encuentras, usa "ING-OTROS" o "GAS-OTROS" respectivamente
- ❌ NO dejes `account`, `amount`, `category` (en ingreso/egreso) vacíos
- ❌ NO uses `movement_type` incorrecto
- ❌ NO generes `description` si el texto no lo justifica

# INSTRUCCIÓN FINAL

Analiza el texto del usuario, determina el `movement_type` correcto y genera ÚNICAMENTE JSON válido con los campos correspondientes. Considera la conversación previa si hay referencias contextuales.
"""

    def __init__(self, provider):
        super().__init__(provider)

    def _build_unified_prompt(
        self,
        text: str,
        accounts: list[str],
        income_cats: list[dict],
        expense_cats: list[dict],
        context: list[dict] | None = None,
    ) -> str:
        """Build unified legacy prompt with all data embedded."""
        accounts_str = "\n".join(f"- {acc}" for acc in accounts)
        income_cats_str = "\n".join(f"- {cat['codigo']} - {cat['nombre']}" for cat in income_cats)
        expense_cats_str = "\n".join(f"- {cat['codigo']} - {cat['nombre']}" for cat in expense_cats)

        # Use simple string replacement to avoid format() interpreting JSON braces
        prompt = self.SYSTEM_PROMPT_LEGACY_UNIFIED
        prompt = prompt.replace("{accounts_str}", accounts_str)
        prompt = prompt.replace("{income_cats_str}", income_cats_str)
        prompt = prompt.replace("{expense_cats_str}", expense_cats_str)

        if context:
            prompt += "\n\n# CONVERSACIÓN PREVIA\n"
            for msg in context:
                role = "Usuario" if msg.get("role") == "user" else "Asistente"
                content = msg.get("content", "") or ""
                prompt += f"{role}: {content}\n"
            prompt += "\n"

        prompt += f"\n# TEXTO DEL USUARIO\n{text}\n\n# OUTPUT\nResponde ÚNICAMENTE con JSON válido. No incluyas markdown, explicaciones ni texto adicional."
        return prompt

    async def _parse_unified(
        self,
        connection,
        text: str,
        context: list[dict],
        expected_type: str,
    ) -> dict | ParsedIncome:
        accounts = self._list_accounts(connection)
        income_cats = self._list_income_categories(connection)
        expense_cats = self._list_expense_categories(connection)

        if not accounts:
            raise AIParsingError("No active accounts available")
        if not income_cats:
            raise AIParsingError("No income categories available")
        if not expense_cats:
            raise AIParsingError("No expense categories available")

        prompt = self._build_unified_prompt(text, accounts, income_cats, expense_cats, context)
        logger.debug("[AI Parser Legacy Unified] Prompt:\n%s", prompt)

        try:
            response = self.provider.call_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a JSON extraction assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            raise AIParsingError(f"LLM API error: {e}") from e

        raw_content = response.choices[0].message.content
        if not raw_content:
            raise AIParsingError("AI returned empty response")

        try:
            parsed_data = json.loads(self._clean_json_markdown(raw_content))
        except json.JSONDecodeError as e:
            raise AIParsingError(f"AI returned invalid JSON: {e}") from e

        movement_type = parsed_data.get("movement_type")
        if not movement_type:
            raise AIParsingError("AI did not specify movement_type in response")

        if movement_type == "income":
            result = self._validate_income(connection, parsed_data)
        elif movement_type == "expense":
            result = self._validate_expense(connection, parsed_data)
        elif movement_type == "transfer":
            result = self._validate_transfer(connection, parsed_data)
        elif movement_type == "credit_create":
            result = self._validate_credit_create(connection, parsed_data)
        else:
            raise AIParsingError(f"Unsupported movement_type: {movement_type}")

        if movement_type != expected_type:
            logger.warning(
                f"[Legacy Unified] Movement type mismatch: expected={expected_type}, detected={movement_type}. Proceeding anyway."
            )

        return result

    def _validate_income(self, connection, data: dict) -> dict | ParsedIncome:
        account_name = data.get("account")
        if not account_name:
            raise AIParsingError("No account identified for income")
        account_entity = self._resolve_account_entity(connection, account_name)
        if not account_entity:
            available = ", ".join(self._list_accounts(connection))
            raise AIParsingError(f"Account '{account_name}' not found. Available: {available}")
        amount_val = data.get("amount")
        if amount_val is None:
            raise AIParsingError("No amount identified")
        try:
            amount = Decimal(str(amount_val))
        except Exception as e:
            raise AIParsingError(f"Invalid amount: {amount_val}") from e
        if amount <= 0:
            raise AIParsingError("Amount must be positive")
        category_codigo = data.get("category", "ING-OTROS")
        resolved_codigo = self._resolve_category_codigo(connection, category_codigo, tipo="INGRESO")
        if not resolved_codigo:
            resolved_codigo = self._resolve_category_codigo(connection, "ING-OTROS", tipo="INGRESO")
            if not resolved_codigo:
                raise AIParsingError("No default INGRESO category (ING-OTROS) available")
        description = data.get("description")
        if description is not None:
            description = str(description)
        return {
            "account_id": account_entity["id"],
            "amount": amount,
            "categoria_codigo": resolved_codigo,
            "description": description,
        }

    def _validate_expense(self, connection, data: dict) -> dict:
        account_name = data.get("account")
        if not account_name:
            raise AIParsingError("No account identified for expense")
        account_entity = self._resolve_account_entity(connection, account_name)
        if not account_entity:
            available = ", ".join(self._list_accounts(connection))
            raise AIParsingError(f"Account '{account_name}' not found. Available: {available}")
        amount_val = data.get("amount")
        if amount_val is None:
            raise AIParsingError("No amount identified")
        try:
            amount = Decimal(str(amount_val))
        except Exception as e:
            raise AIParsingError(f"Invalid amount: {amount_val}") from e
        if amount <= 0:
            raise AIParsingError("Amount must be positive")
        category_codigo = data.get("category", "GAS-OTROS")
        resolved_codigo = self._resolve_category_codigo(connection, category_codigo, tipo="GASTO")
        if not resolved_codigo:
            resolved_codigo = self._resolve_category_codigo(connection, "GAS-OTROS", tipo="GASTO")
            if not resolved_codigo:
                raise AIParsingError("No default GASTO category (GAS-OTROS) for expense")
        description = data.get("description")
        if description is not None:
            description = str(description)
        return {
            "account_id": account_entity["id"],
            "amount": amount,
            "categoria_codigo": resolved_codigo,
            "description": description,
        }

    def _validate_transfer(self, connection, data: dict) -> dict:
        source_name = data.get("source_account")
        target_name = data.get("target_account")
        if not source_name or not target_name:
            raise AIParsingError("Missing source_account or target_account in transfer")
        if source_name == target_name:
            raise AIParsingError("Source and target accounts must be different")
        source_entity = self._resolve_account_entity(connection, source_name)
        target_entity = self._resolve_account_entity(connection, target_name)
        if not source_entity:
            raise AIParsingError(f"Source account '{source_name}' not found")
        if not target_entity:
            raise AIParsingError(f"Target account '{target_name}' not found")
        amount_val = data.get("amount")
        if amount_val is None:
            raise AIParsingError("No amount identified for transfer")
        try:
            amount = Decimal(str(amount_val))
        except Exception as e:
            raise AIParsingError(f"Invalid amount: {amount_val}") from e
        if amount <= 0:
            raise AIParsingError("Amount must be positive")
        description = data.get("description")
        if description is not None:
            description = str(description)
        return {
            "source_account_id": source_entity["id"],
            "target_account_id": target_entity["id"],
            "amount": amount,
            "description": description,
        }

    def _validate_credit_create(self, connection, data: dict) -> dict:
        """Validate data for creating a new credit. Expected: type, total_amount, due_date, description (optional)."""
        credit_type_raw = data.get("type")
        if not credit_type_raw:
            raise AIParsingError("No credit type specified for credit creation")
        type_mapping = {
            "CXC": "CREDIT_SALE",
            "CXP": "CREDIT_PURCHASE",
            "CREDIT_SALE": "CREDIT_SALE",
            "CREDIT_PURCHASE": "CREDIT_PURCHASE",
            "VENTA_CREDITO": "CREDIT_SALE",
            "COMPRA_CREDITO": "CREDIT_PURCHASE",
        }
        normalized_type = type_mapping.get(str(credit_type_raw).upper())
        if not normalized_type:
            raise AIParsingError(f"Invalid credit type: {credit_type_raw}. Use one of: CXC, CXP, CREDIT_SALE, CREDIT_PURCHASE")
        total_amount_val = data.get("total_amount") or data.get("amount")
        if total_amount_val is None:
            raise AIParsingError("No total_amount provided for credit creation")
        try:
            total_amount = Decimal(str(total_amount_val))
        except Exception as e:
            raise AIParsingError(f"Invalid total_amount: {total_amount_val}") from e
        if total_amount <= 0:
            raise AIParsingError("total_amount must be positive")
        due_date_str = data.get("due_date")
        if not due_date_str:
            raise AIParsingError("No due_date provided for credit creation")
        try:
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
        except Exception as e:
            raise AIParsingError(f"Invalid due_date: {due_date_str}") from e
        description = data.get("description")
        if description is not None:
            description = str(description)
        return {
            "type": normalized_type,
            "total_amount": total_amount,
            "due_date": due_date,
            "description": description,
        }

    async def parse_income_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> ParsedIncome:
        context_norm = await self._normalize_context(context)
        result = await self._parse_unified(connection, text, context_norm, expected_type="income")
        if isinstance(result, ParsedIncome):
            return result
        try:
            return ParsedIncome(**result)
        except Exception as e:
            raise AIParsingError(f"Invalid parsed income data: {e}") from e

    async def parse_expense_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        context_norm = await self._normalize_context(context)
        return await self._parse_unified(connection, text, context_norm, expected_type="expense")

    async def parse_transfer_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        context_norm = await self._normalize_context(context)
        return await self._parse_unified(connection, text, context_norm, expected_type="transfer")

    async def parse_credit_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        context_norm = await self._normalize_context(context)
        result = await self._parse_unified(connection, text, context_norm, expected_type="credit_create")
        if not result.get("type") or not result.get("total_amount") or not result.get("due_date"):
            raise AIParsingError("Missing required credit fields")
        return result
