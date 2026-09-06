"""inbound_channels_tables

Revision ID: a1b2c3d4e5f6
Revises: 6ee79b0f52a3
Create Date: 2026-09-06 20:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6ee79b0f52a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("inbound_default_workspace_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_users_inbound_default_workspace_id",
        "users",
        ["inbound_default_workspace_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_users_inbound_default_workspace_id",
        "users",
        "workspaces",
        ["inbound_default_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "inbound_idempotency",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "channel",
            "provider_message_id",
            name="uq_inbound_idempotency_channel_message",
        ),
    )
    op.create_index(
        "ix_inbound_idempotency_channel",
        "inbound_idempotency",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_inbound_idempotency_workspace_id",
        "inbound_idempotency",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "whatsapp_identity_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("wa_id", sa.String(length=64), nullable=True),
        sa.Column("pending_code", sa.String(length=16), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("phone", name="uq_whatsapp_identity_phone"),
    )
    op.create_index(
        "ix_whatsapp_identity_links_user_id",
        "whatsapp_identity_links",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_whatsapp_identity_links_wa_id",
        "whatsapp_identity_links",
        ["wa_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_whatsapp_identity_links_wa_id", table_name="whatsapp_identity_links")
    op.drop_index("ix_whatsapp_identity_links_user_id", table_name="whatsapp_identity_links")
    op.drop_table("whatsapp_identity_links")

    op.drop_index("ix_inbound_idempotency_workspace_id", table_name="inbound_idempotency")
    op.drop_index("ix_inbound_idempotency_channel", table_name="inbound_idempotency")
    op.drop_table("inbound_idempotency")

    op.drop_constraint("fk_users_inbound_default_workspace_id", "users", type_="foreignkey")
    op.drop_index("ix_users_inbound_default_workspace_id", table_name="users")
    op.drop_column("users", "inbound_default_workspace_id")
