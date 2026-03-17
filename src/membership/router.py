from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.security.permissions import require_roles
from membership.repository import MembershipRepository
from membership.schemas import MemberInvite, MemberRead, MemberRoleUpdate
from membership.service import invite_member, remove_member, change_member_role


router = APIRouter(prefix="/workspaces/members", tags=["membership"])


@router.get("/", response_model=list[MemberRead])
async def list_members(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = MembershipRepository(db, workspace_id=ctx.workspace_id)
    pairs = await repo.list_members()
    return [
        MemberRead(user_id=m.user_id, email=u.email, role=m.role)
        for (m, u) in pairs
    ]


@router.post("/", response_model=MemberRead)
async def invite(
    data: MemberInvite,
    ctx: RequestContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    repo = MembershipRepository(db, workspace_id=ctx.workspace_id)
    membership = await invite_member(repo=repo, ctx=ctx, email=data.email, role=data.role)

    user = await repo.get_user_by_email(email=data.email)
    # user must exist if invite succeeded
    assert user is not None
    return MemberRead(user_id=membership.user_id, email=user.email, role=membership.role)


@router.patch("/{user_id}", response_model=MemberRead)
async def set_role(
    user_id: int,
    data: MemberRoleUpdate,
    ctx: RequestContext = Depends(require_roles("owner")),
    db: AsyncSession = Depends(get_session),
):
    repo = MembershipRepository(db, workspace_id=ctx.workspace_id)
    membership = await change_member_role(repo=repo, ctx=ctx, user_id=user_id, role=data.role)
    # fetch user for response
    pairs = await repo.list_members()
    email = next((u.email for (m, u) in pairs if m.user_id == user_id), "")
    return MemberRead(user_id=membership.user_id, email=email, role=membership.role)


@router.delete("/{user_id}", status_code=204)
async def delete_member(
    user_id: int,
    ctx: RequestContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    repo = MembershipRepository(db, workspace_id=ctx.workspace_id)
    await remove_member(repo=repo, ctx=ctx, user_id=user_id)
    return None

