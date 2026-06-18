"""Service layer for business rules."""

from app.services.accounts import (
    create_account,
    delete_account,
    get_account_detail,
    list_accounts,
)
from app.services.auth import authenticate_user, ensure_admin_user
# from app.services.cierres import (  # Deshabilitado temporalmente: tabla 'transacciones' no definida
#     create_cierre,
#     get_cierre,
#     get_cierre_by_usuario_dia,
#     list_cierres,
#     lock_cierre,
# )
from app.services.credits import (
    create_credit,
    list_credits,
    get_credit_summary,
    pay_credit,
    update_credit,
)
from app.services.idempotency import get_existing_response
from app.services.movements import (
    add_expense,
    add_income,
    add_transfer,
    delete_movement,
    list_recent_movements,
    update_movement,
)
from app.services.sync import process_sync
from app.services.turns import (
    close_global_turn,
    close_turn,
    get_active_turn,
    get_global_turn_summary,
    get_historical_summary,
    list_turn_groups,
    open_global_turn,
    open_turn,
)

__all__ = [
    # accounts
    "create_account",
    "delete_account",
    "get_account_detail",
    "list_accounts",
    # auth
    "authenticate_user",
    "ensure_admin_user",
    # cierres (disabled pending proper schema)
    # "create_cierre",
    # "get_cierre",
    # "get_cierre_by_usuario_dia",
    # "list_cierres",
    # "lock_cierre",
    # credits
    "create_credit",
    "list_credits",
    "get_credit_summary",
    "pay_credit",
    "update_credit",
    # idempotency
    "get_existing_response",
    # movements
    "add_income",
    "add_expense",
    "add_transfer",
    "delete_movement",
    "list_recent_movements",
    "update_movement",
    # sync
    "process_sync",
    # turns
    "open_turn",
    "close_turn",
    "get_active_turn",
    "open_global_turn",
    "close_global_turn",
    "get_global_turn_summary",
    "get_historical_summary",
    "list_turn_groups",
]
