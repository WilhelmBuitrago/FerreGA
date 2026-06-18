from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.types import (
    CategoriaTipo,
    EstadoCierre,
    MovementType,
    TurnStatus,
    CreditType,
    CreditStatus,
)

metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", String, primary_key=True),
    Column("nombre", String, nullable=False),
    Column("password_hash", String),
    Column("role", String, nullable=False, server_default=text("'admin'")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

cierres = Table(
    "cierres",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column("fecha", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "usuario_id",
        String,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("balance_esperado", Numeric(12, 2), nullable=False),
    Column("balance_real", Numeric(12, 2), nullable=False),
    Column("diferencia", Numeric(12, 2), nullable=False),
    Column(
        "estado",
        Enum(EstadoCierre, name="estado_cierre"),
        nullable=False,
        server_default=text("'ABIERTO'"),
    ),
    Column("edit_lock", Boolean, nullable=False, server_default=text("false")),
    Column("notas", Text),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("balance_real >= 0", name="ck_cierres_balance_real_non_negative"),
    Index("ix_cierres_usuario_fecha", "usuario_id", "fecha"),
    Index("ix_cierres_estado", "estado"),
)


accounts = Table(
    "accounts",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column("name", String, nullable=False, unique=True),
    Column("turn_amount", Numeric(12, 2), nullable=False, server_default=text("0")),
    Column("account_amount", Numeric(12, 2), nullable=False, server_default=text("0")),
    Column("difference", Numeric(12, 2), nullable=False, server_default=text("0")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)


turns = Table(
    "turns",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "turn_group_id",
        UUID(as_uuid=True),
        nullable=False,
    ),
    Column(
        "account_id",
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("start_amount", Numeric(12, 2), nullable=False, server_default=text("0")),
    Column("end_amount", Numeric(12, 2)),
    Column(
        "status",
        Enum(TurnStatus, name="turn_status"),
        nullable=False,
        server_default=text("'OPEN'"),
    ),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("closed_at", DateTime(timezone=True)),
    Index("ix_turns_account_id", "account_id"),
    Index("ix_turns_group_id", "turn_group_id"),
)

# Nota: La restricción de un solo turno abierto por cuenta se maneja en código
# (ver open_turn y open_global_turn). En PostgreSQL podría usarse un índice parcial,
# pero SQLite no lo soporta, así que lo eliminamos para compatibilidad.


categorias = Table(
    "categorias",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column("codigo", String, nullable=False, unique=True),
    Column("nombre", String, nullable=False),
    Column(
        "tipo",
        Enum(CategoriaTipo, name="categoria_tipo"),
        nullable=False,
    ),
    Column("grupo", String, nullable=True),
    Column("activo", Boolean, nullable=False, server_default=text("true")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)


movements = Table(
    "movements",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "turn_id",
        UUID(as_uuid=True),
        ForeignKey("turns.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "account_id",
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
    ),
    Column(
        "type",
        Enum(MovementType, name="movement_type"),
        nullable=False,
    ),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("description", Text),
    Column(
        "categoria_codigo",
        String,
        ForeignKey("categorias.codigo", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column(
        "timestamp", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("is_outgoing", Boolean, nullable=False, server_default=text("false")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    CheckConstraint("amount > 0", name="ck_movements_amount_positive"),
    Index("ix_movements_turn_id", "turn_id"),
)


command_log = Table(
    "command_log",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "idempotency_key",
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
    ),
    Column("command_type", String, nullable=False),
    Column("response", Text, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_command_log_created_at", "created_at"),
)

credits = Table(
    "credits",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "account_id",
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
    ),
    Column(
        "type",
        Enum(CreditType, name="credit_type"),
        nullable=False,
    ),
    Column("total_amount", Numeric(12, 2), nullable=False),
    Column("paid_amount", Numeric(12, 2), nullable=False, server_default=text("0")),
    Column(
        "due_date",
        DateTime(timezone=True),
        nullable=False,
    ),
    Column(
        "status",
        Enum(CreditStatus, name="credit_status"),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    ),
    Column("description", Text),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("total_amount > 0", name="ck_credits_total_positive"),
    CheckConstraint(
        "paid_amount >= 0 AND paid_amount <= total_amount", name="ck_credits_paid_valid"
    ),
    Index("ix_credits_account_id", "account_id"),
    Index("ix_credits_due_date", "due_date"),
    Index("ix_credits_status", "status"),
)
