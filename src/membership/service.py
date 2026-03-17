from fastapi import HTTPException

from core.security.context import RequestContext
from membership.repository import MembershipRepository


ALLOWED_ROLES = {"owner", "admin", "member"}


def _normalize_role(role: str) -> str:
    role = role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    return role


async def invite_member(
    *,
    repo: MembershipRepository,
    ctx: RequestContext,
    email: str,
    role: str,
):
    """
    Invite an existing user (by email) into the current workspace.

    - owner can invite admin/member
    - admin can invite member only
    """

    role = _normalize_role(role)
    if role == "owner":
        raise HTTPException(status_code=400, detail="Cannot invite an owner")
    if ctx.role == "admin" and role == "admin":
        raise HTTPException(status_code=403, detail="Only owner can invite admins")

    user = await repo.get_user_by_email(email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await repo.get_member(user_id=user.id)
    if existing:
        raise HTTPException(status_code=400, detail="User already a member")

    return await repo.add_member(user_id=user.id, role=role)


async def change_member_role(
    *,
    repo: MembershipRepository,
    ctx: RequestContext,
    user_id: int,
    role: str,
):
    role = _normalize_role(role)
    if role == "owner":
        raise HTTPException(status_code=400, detail="Cannot assign owner role")
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can change roles")

    member = await repo.get_member(user_id=user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return await repo.update_role(member, role=role)


async def remove_member(
    *,
    repo: MembershipRepository,
    ctx: RequestContext,
    user_id: int,
):
    if ctx.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if user_id == ctx.user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    member = await repo.get_member(user_id=user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if ctx.role == "admin" and member.role in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin cannot remove admin/owner")

    await repo.remove_member(user_id=user_id)

