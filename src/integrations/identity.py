"""Resolve inbound senders to user + workspace."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.models import User, WorkspaceUser


@dataclass(frozen=True)
class ResolvedIdentity:
    user_id: int
    workspace_id: int
    role: str
    email: str | None = None


async def resolve_email_sender(
    db: AsyncSession,
    from_email: str,
) -> ResolvedIdentity:
    email = from_email.strip().lower()
    stmt = (
        select(User)
        .where(func.lower(User.email) == email)
        .options(selectinload(User.workspaces))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown email sender.",
        )
    return await resolve_default_workspace(db, user)


async def resolve_default_workspace(
    db: AsyncSession,
    user: User,
) -> ResolvedIdentity:
    """
    Prefer users.inbound_default_workspace_id when it is a valid membership;
    else sole membership; else earliest membership by (tenant_id, user_id).
    """
    memberships = list(user.workspaces or [])
    if not memberships:
        # Reload if relationship was empty / not loaded
        stmt = (
            select(WorkspaceUser)
            .where(WorkspaceUser.user_id == user.id)
            .order_by(WorkspaceUser.tenant_id.asc(), WorkspaceUser.user_id.asc())
        )
        result = await db.execute(stmt)
        memberships = list(result.scalars().all())

    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender has no workspace membership.",
        )

    default_wid = getattr(user, "inbound_default_workspace_id", None)
    if default_wid is not None:
        for m in memberships:
            if m.tenant_id == default_wid:
                return ResolvedIdentity(
                    user_id=user.id,
                    workspace_id=m.tenant_id,
                    role=m.role,
                    email=user.email,
                )

    if len(memberships) == 1:
        m = memberships[0]
        return ResolvedIdentity(
            user_id=user.id,
            workspace_id=m.tenant_id,
            role=m.role,
            email=user.email,
        )

    memberships_sorted = sorted(memberships, key=lambda m: (m.tenant_id, m.user_id))
    m = memberships_sorted[0]
    return ResolvedIdentity(
        user_id=user.id,
        workspace_id=m.tenant_id,
        role=m.role,
        email=user.email,
    )


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+") and digits.isdigit():
        digits = "+" + digits
    return digits


async def resolve_whatsapp_sender(
    db: AsyncSession,
    phone_or_wa_id: str,
) -> ResolvedIdentity:
    from integrations.models import WhatsAppIdentityLink

    phone = normalize_phone(phone_or_wa_id)
    stmt = select(WhatsAppIdentityLink).where(
        (WhatsAppIdentityLink.phone == phone)
        | (WhatsAppIdentityLink.wa_id == phone_or_wa_id.strip())
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link is None or link.verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unlinked WhatsApp sender.",
        )

    user_stmt = (
        select(User)
        .where(User.id == link.user_id)
        .options(selectinload(User.workspaces))
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unlinked WhatsApp sender.",
        )
    return await resolve_default_workspace(db, user)
