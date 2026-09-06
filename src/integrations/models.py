"""Inbound identity, idempotency, and WhatsApp link models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base
from core.database.mixins import TimestampMixin


class InboundIdempotency(Base, TimestampMixin):
    """Maps (channel, provider_message_id) → created note_id for dedupe."""

    __tablename__ = "inbound_idempotency"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "provider_message_id",
            name="uq_inbound_idempotency_channel_message",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False)


class WhatsAppIdentityLink(Base, TimestampMixin):
    """Verified (or pending) WhatsApp phone ↔ user link."""

    __tablename__ = "whatsapp_identity_links"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_whatsapp_identity_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    wa_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pending_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
