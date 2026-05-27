"""
SQLAlchemy models for AI conversation persistence.

Tables:
  ai_threads  — conversation threads (one per user conversation)
  ai_messages — individual messages within a thread

These are the PRODUCT layer — what the user sees in the UI.
LangGraph's AsyncPostgresSaver (Slice 6) creates its own internal tables.
Both layers are linked only by thread_id string — never via FK.

IMPORT LAW: Only SQLAlchemy, stdlib, and project base/mixins.
No ai.*, no FastAPI, no pydantic business logic here.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base
from core.database.mixins import TimestampMixin, WorkspaceTenantMixin


class AIThread(Base, WorkspaceTenantMixin, TimestampMixin):
    """
    A conversation thread between a user and the AI assistant.

    workspace_id scopes threads to a workspace — cross-workspace access
    is rejected at the repository layer (workspace_id filter on every query).
    created_by is the user who started the thread.

    LangGraph link: thread.id (as string) becomes the LangGraph thread_id
    in Slice 6. No FK — just string linking.
    """

    __tablename__ = "ai_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    created_by: Mapped[int] = mapped_column(index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )

    messages: Mapped[list["AIMessage"]] = relationship(
        "AIMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<AIThread id={self.id} workspace={self.workspace_id}>"


class AIMessage(Base):
    """
    A single message in a conversation thread.

    role must be one of: 'user', 'assistant', 'tool'
    citations stores the note references used to generate the assistant response.
    token_count is approximate — used for context budget calculations.
    """

    __tablename__ = "ai_messages"

    VALID_ROLES = ("user", "assistant", "tool")

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    citations: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'tool')",
            name="ai_messages_role_check",
        ),
        Index("idx_ai_messages_thread_created", "thread_id", "created_at"),
    )

    thread: Mapped["AIThread"] = relationship(
        "AIThread",
        back_populates="messages",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<AIMessage id={self.id} role={self.role} thread={self.thread_id}>"
