"""Repository interfaces for data access."""

from app.repositories.accounts import (
    create_account,
    delete_account,
    get_account,
    get_account_by_name,
    list_accounts,
    update_account,
)
from app.repositories.cierres import (
    create_cierre,
    get_cierre,
    get_cierre_by_usuario_dia,
    list_cierres,
    lock_cierre,
)
from app.repositories.credits import (
    create_credit,
    get_credit,
    list_credits,
    update_credit,
)
from app.repositories.idempotency import create_command_log, get_command_log
from app.repositories.movements import (
    create_movement,
    get_movement,
    get_movement_sums,
    list_movements_by_turn,
    soft_delete_movement,
    update_movement,
)
from app.repositories.turns import (
    close_turn,
    create_closed_turn,
    create_turn,
    get_active_group_id,
    get_active_turn,
    get_latest_closed_group_id,
    get_turn,
    list_turns_by_group,
    list_turns_for_account,
    update_closed_turn_amount,
)
from app.repositories.users import (
    create_user,
    get_user_by_id,
    update_user_credentials,
)

__all__ = [
    # accounts
    "create_account",
    "delete_account",
    "get_account",
    "get_account_by_name",
    "list_accounts",
    "update_account",
    # cierres
    "create_cierre",
    "get_cierre",
    "get_cierre_by_usuario_dia",
    "list_cierres",
    "lock_cierre",
    # credits
    "create_credit",
    "get_credit",
    "list_credits",
    "update_credit",
    # idempotency
    "get_command_log",
    "create_command_log",
    # movements
    "create_movement",
    "get_movement",
    "get_movement_sums",
    "list_movements_by_turn",
    "soft_delete_movement",
    "update_movement",
    # turns
    "create_turn",
    "create_closed_turn",
    "get_turn",
    "get_active_turn",
    "list_turns_for_account",
    "get_active_group_id",
    "get_latest_closed_group_id",
    "list_turns_by_group",
    "close_turn",
    "update_closed_turn_amount",
    # users
    "get_user_by_id",
    "create_user",
    "update_user_credentials",
]
