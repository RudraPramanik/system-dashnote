"""add_extracted_text_summary_tags_to_files

Revision ID: 95fb65156e52
Revises: d3339fc62797
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "95fb65156e52"
down_revision: Union[str, Sequence[str], None] = "d3339fc62797"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column(
            "extracted_text",
            sa.Text(),
            nullable=True,
            comment="Raw extracted text from file binary — populated by worker",
        ),
    )
    op.add_column(
        "files",
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
            comment="AI-generated summary — populated by generate_file_metadata worker",
        ),
    )
    op.add_column(
        "files",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="AI-generated tags — populated by generate_file_metadata worker",
        ),
    )


def downgrade() -> None:
    op.drop_column("files", "tags")
    op.drop_column("files", "summary")
    op.drop_column("files", "extracted_text")
