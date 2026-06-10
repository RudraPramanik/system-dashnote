"""add_tags_to_notes

Revision ID: 6ee79b0f52a3
Revises: 95fb65156e52
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6ee79b0f52a3"
down_revision: Union[str, Sequence[str], None] = "95fb65156e52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="AI-generated tags — populated by generate_note_tags worker",
        ),
    )


def downgrade() -> None:
    op.drop_column("notes", "tags")
