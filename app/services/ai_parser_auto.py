"""
Auto AI parser mode - uses intent tool + dynamic context.
No list_* tools. Model calls intent(tipo) to set context, then calls crear_*.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from .ai_parser_base import AIParserBase, AIParsingError

logger = logging.getLogger(__name__)


class AIParserAuto(AIParserBase):
    """Auto parser with intent-based dynamic context. No list_* tools."""

    BASE_SYSTEM_PROMPT = """Eres un asistente contable que registra movimientos financieros usando herramientas. NO devuelvas JSON manualmente.

# HERRAMIENTAS

- intent(tipo): Especifica la intención del usuario. Tipos: "ingreso", "egreso", "transferencia", "credito". Llama a esta herramienta al iniciar o cuando cambie la intención.
- crear_ingreso(cuenta, monto, categoria_codigo, descripcion=None)
- crear_egreso(cuenta, monto, categoria_codigo, descripcion=None)
- crear_transferencia(cuenta_origen, cuenta_destino, monto, descripcion=None)
- crear_credito(tipo_credito, monto, fecha_vencimiento, descripcion=None)

# CONTEXTO DINÁMICO

El sistema te proporcionará en cada turno un objeto JSON llamado "Contexto actual" que contiene:
- intent: tipo de movimiento actual
- accounts: lista de nombres de cuentas activas (presente para intent=ingreso/egreso/transferencia)
- categories: lista de {codigo, nombre} de categorías (presente para intent=ingreso/egreso)
- last_movement: último movimiento creado (si existe)

# REGLAS

1. Usa LOS DATOS del "Contexto actual" para elegir cuenta y categoría. NO inventes nombres o códigos.
2. Cuando recibas un nuevo mensaje del usuario:
   - Si la intención cambió o no está definida, llama a intent(tipo=...).
   - Luego, usa la herramienta de creación correspondiente al intent actual.
3. Para modificar un movimiento anterior, utiliza los valores de "last_movement" del contexto y cambia solo lo necesario.
4. No generes texto adicional. Solo ejecuta herramientas.

# FLUJO TÍPICO

1. Usuario: "Registro una venta de 50000 en banco"
   Asistente: intent(tipo="ingreso")
   Sistema actualiza contexto con accounts y categories de ingreso.
2. Asistente (segundo turno): crear_ingreso(cuenta="Banco", monto=50000, categoria_codigo="ING-VENTAS-CTO")

Si el usuario luego dice: "Mejor transfiere 20000 de banco a nequi", el asistente debe:
- Detectar cambio → intent(tipo="transferencia")
- Sistema actualiza contexto (solo accounts, limpia categories y last_movement)
- Luego: crear_transferencia(cuenta_origen="Banco", cuenta_destino="Nequi", monto=20000)

# IMPORTANTE

- No llames a listar_cuentas ni listar_categorias; ya están en el contexto.
- Respeta mayúsculas/acentos de nombres y códigos tal como vienen en el contexto.
- Fecha para créditos: YYYY-MM-DD. Convierte dates del usuario.
"""

    def __init__(self, provider):
        super().__init__(provider)

    async def _run_agent_flow(
        self, connection, text: str, context: list[dict], expected_intent: str
    ):
        normalized_context = []
        for msg in context:
            if isinstance(msg, dict):
                normalized_context.append(msg)
            else:
                normalized_context.append({
                    "role": getattr(msg, "role", "user"),
                    "content": getattr(msg, "content", None) or ""
                })

        dynamic_context = {}
        created_result = None
        max_iterations = 5

        def build_system_content():
            base = self.BASE_SYSTEM_PROMPT
            if dynamic_context:
                base += f"\n\nContexto actual:\n{json.dumps(dynamic_context, ensure_ascii=False, indent=2)}"
            else:
                base += "\n\nContexto actual: (vacío, espera que uses intent para configurar)"
            return base

        messages = [{"role": "system", "content": build_system_content()}]
        for msg in normalized_context:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": text})

        for iteration in range(max_iterations):
            logger.info(f"[AI Parser Auto v2] Intent flow iteration {iteration+1}/{max_iterations}")
            try:
                response = self.provider.call_chat_completion(
                    messages=messages,
                    tools=self.TOOLS_SCHEMA,
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"[AI Parser Auto v2] LLM API error: {e}")
                raise AIParsingError(f"LLM API error: {e}") from e

            msg = response.choices[0].message
            logger.info(f"[AI Parser Auto v2] Message: role={msg.role}, content={msg.content!r}, tool_calls={msg.tool_calls}")

            assistant_msg = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                tool_calls_list = []
                for tc in msg.tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                assistant_msg["tool_calls"] = tool_calls_list
            messages.append(assistant_msg)

            if not msg.tool_calls:
                if not created_result:
                    raise AIParsingError("Model did not call any tool to create the movement")
                break

            context_updated = False
            for tool_call in msg.tool_calls:
                func_name_raw = tool_call.function.name
                func_name = func_name_raw
                known_tools = {t["function"]["name"] for t in self.TOOLS_SCHEMA}
                if func_name not in known_tools:
                    for known in known_tools:
                        if known in func_name or func_name in known:
                            logger.warning(f"[AI Parser Auto v2] Remapping tool '{func_name}' -> '{known}'")
                            func_name = known
                            break
                    else:
                        logger.warning(f"[AI Parser Auto v2] Unknown tool '{func_name}', skipping")
                        messages.append({
                            "role": "tool",
                            "content": json.dumps({"error": f"Unknown tool: {func_name}"}),
                            "tool_call_id": tool_call.id,
                        })
                        continue

                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"[AI Parser Auto v2] Invalid JSON arguments: {tool_call.function.arguments}")
                    messages.append({
                        "role": "tool",
                        "content": json.dumps({"error": f"Invalid arguments JSON: {e}"}),
                        "tool_call_id": tool_call.id,
                    })
                    continue

                logger.info(f"[AI Parser Auto v2] Executing tool: {func_name} args={args}")
                result = None
                try:
                    if func_name == "intent":
                        tipo = args.get("tipo")
                        if not tipo:
                            result = {"error": "Missing 'tipo' parameter for intent"}
                        else:
                            dynamic_context.clear()
                            dynamic_context["intent"] = tipo
                            accounts = self._listar_cuentas(connection)
                            dynamic_context["accounts"] = accounts
                            if tipo in ("ingreso", "egreso"):
                                cats = self._listar_categorias(connection, tipo)
                                dynamic_context["categories"] = [
                                    {"codigo": c.get("codigo") or c.get("id"), "nombre": c.get("nombre")} for c in cats
                                ]
                            if tipo == "credito":
                                dynamic_context.pop("accounts", None)
                                dynamic_context.pop("categories", None)
                                dynamic_context.pop("last_movement", None)
                            result = {"status": "intent recorded", "tipo": tipo}
                            context_updated = True
                            logger.debug(f"[AI Parser Auto v2] Intent updated dynamic_context: intent={tipo}, accounts={len(dynamic_context.get('accounts', []))}, categories={len(dynamic_context.get('categories', []))}")
                    elif func_name == "crear_ingreso":
                        cuenta = args.get("cuenta")
                        monto = args.get("monto")
                        cat = args.get("categoria_codigo")
                        if not cuenta or monto is None or not cat:
                            result = {"error": "Missing required parameters for crear_ingreso"}
                        else:
                            result = self._crear_ingreso(connection, cuenta, monto, cat, args.get("descripcion"))
                            if "error" not in result:
                                created_result = result
                                dynamic_context["last_movement"] = {
                                    "cuenta": cuenta,
                                    "monto": monto,
                                    "categoria_codigo": cat,
                                    "descripcion": args.get("descripcion"),
                                    "tipo": "ingreso"
                                }
                                context_updated = True
                    elif func_name == "crear_egreso":
                        cuenta = args.get("cuenta")
                        monto = args.get("monto")
                        cat = args.get("categoria_codigo")
                        if not cuenta or monto is None or not cat:
                            result = {"error": "Missing required parameters for crear_egreso"}
                        else:
                            result = self._crear_egreso(connection, cuenta, monto, cat, args.get("descripcion"))
                            if "error" not in result:
                                created_result = result
                                dynamic_context["last_movement"] = {
                                    "cuenta": cuenta,
                                    "monto": monto,
                                    "categoria_codigo": cat,
                                    "descripcion": args.get("descripcion"),
                                    "tipo": "egreso"
                                }
                                context_updated = True
                    elif func_name == "crear_transferencia":
                        cuenta_origen = args.get("cuenta_origen")
                        cuenta_destino = args.get("cuenta_destino")
                        monto = args.get("monto")
                        if not cuenta_origen or not cuenta_destino or monto is None:
                            result = {"error": "Missing required parameters for crear_transferencia"}
                        else:
                            result = self._crear_transferencia(connection, cuenta_origen, cuenta_destino, monto, args.get("descripcion"))
                            if "error" not in result:
                                created_result = result
                                dynamic_context["last_movement"] = {
                                    "cuenta_origen": cuenta_origen,
                                    "cuenta_destino": cuenta_destino,
                                    "monto": monto,
                                    "descripcion": args.get("descripcion"),
                                    "tipo": "transferencia"
                                }
                                context_updated = True
                    elif func_name == "crear_credito":
                        tipo_credito = args.get("tipo_credito")
                        monto = args.get("monto")
                        fecha_vencimiento = args.get("fecha_vencimiento")
                        if not tipo_credito or monto is None or not fecha_vencimiento:
                            result = {"error": "Missing required parameters for crear_credito"}
                        else:
                            result = self._crear_credito(connection, tipo_credito, monto, fecha_vencimiento, args.get("descripcion"))
                            if "error" not in result:
                                created_result = result
                                dynamic_context["last_movement"] = {
                                    "tipo_credito": tipo_credito,
                                    "monto": monto,
                                    "fecha_vencimiento": fecha_vencimiento,
                                    "descripcion": args.get("descripcion"),
                                    "tipo": "credito"
                                }
                                context_updated = True
                    else:
                        result = {"error": f"Unknown tool {func_name}"}
                except AIParsingError as e:
                    result = {"error": str(e)}
                except Exception as e:
                    logger.exception(f"[AI Parser Auto v2] Tool execution error: {e}")
                    result = {"error": f"Tool execution failed: {e}"}

                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, default=str),
                    "tool_call_id": tool_call.id,
                })
                logger.info(f"[AI Parser Auto v2] Tool result: {result}")

            if context_updated:
                messages[0]["content"] = build_system_content()
                logger.debug(f"[AI Parser Auto v2] Updated dynamic_context:\n{json.dumps(dynamic_context, ensure_ascii=False, indent=2)}")

            if created_result is not None:
                logger.info("[AI Parser Auto v2] Creation succeeded, ending agent flow.")
                break

        if not created_result:
            raise AIParsingError("No creation tool was successfully executed by the model")

        # Attach movement_type for unified response
        if isinstance(created_result, dict):
            created_result["movement_type"] = dynamic_context.get("intent")

        return created_result

    async def parse_income_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        return await self._run_agent_flow(connection, text, context or [], "income")

    async def parse_expense_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        return await self._run_agent_flow(connection, text, context or [], "expense")

    async def parse_transfer_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        return await self._run_agent_flow(connection, text, context or [], "transfer")

    async def parse_credit_text(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        return await self._run_agent_flow(connection, text, context or [], "credit_create")

    async def parse_auto(
        self, connection, text: str, context: list[dict] | None = None
    ) -> dict:
        return await self._run_agent_flow(connection, text, context or [], "auto")
