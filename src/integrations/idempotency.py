"""Idempotency helpers for inbound ingest."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.models import InboundIdempotency


async def get_existing_ingest(
    db: AsyncSession,
    *,
    channel: str,
    provider_message_id: str,
) -> InboundIdempotency | None:
    stmt = select(InboundIdempotency).where(
        InboundIdempotency.channel == channel,
        InboundIdempotency.provider_message_id == provider_message_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def record_ingest(
    db: AsyncSession,
    *,
    channel: str,
    provider_message_id: str,
    note_id: int,
    workspace_id: int,
    user_id: int,
) -> InboundIdempotency:
    row = InboundIdempotency(
        channel=channel,
        provider_message_id=provider_message_id,
        note_id=note_id,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
