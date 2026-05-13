"""create files and attachments

Revision ID: 202605131530
Revises: 921927f71545
Create Date: 2026-05-13 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202605131530"
down_revision: Union[str, Sequence[str], None] = "921927f71545"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_files_workspace_created_by",
        "files",
        ["workspace_id", "created_by"],
        unique=False,
    )
    op.create_index(
        "ix_files_workspace_private",
        "files",
        ["workspace_id", "is_private"],
        unique=False,
    )

    op.create_table(
        "note_attachments",
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("note_id", "file_id"),
    )
    op.create_index(
        "ix_note_attachments_workspace",
        "note_attachments",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_note_attachments_workspace", table_name="note_attachments")
    op.drop_table("note_attachments")
    op.drop_index("ix_files_workspace_private", table_name="files")
    op.drop_index("ix_files_workspace_created_by", table_name="files")
    op.drop_table("files")
