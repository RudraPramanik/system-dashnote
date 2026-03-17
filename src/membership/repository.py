from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User, WorkspaceUser


class MembershipRepository:
    def __init__(self, session: AsyncSession, workspace_id: int):
        self.session = session
        self.workspace_id = workspace_id

    async def list_members(self) -> list[tuple[WorkspaceUser, User]]:
        stmt = (
            select(WorkspaceUser, User)
            .join(User, User.id == WorkspaceUser.user_id)
            .where(WorkspaceUser.tenant_id == self.workspace_id)
            .order_by(WorkspaceUser.role, WorkspaceUser.user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_member(self, *, user_id: int) -> WorkspaceUser | None:
        stmt = select(WorkspaceUser).where(
            WorkspaceUser.tenant_id == self.workspace_id,
            WorkspaceUser.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, *, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(self, *, user_id: int, role: str) -> WorkspaceUser:
        member = WorkspaceUser(
            user_id=user_id,
            tenant_id=self.workspace_id,
            role=role,
        )
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def update_role(self, member: WorkspaceUser, *, role: str) -> WorkspaceUser:
        member.role = role
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove_member(self, *, user_id: int) -> None:
        stmt = delete(WorkspaceUser).where(
            WorkspaceUser.tenant_id == self.workspace_id,
            WorkspaceUser.user_id == user_id,
        )
        await self.session.execute(stmt)
        await self.session.commit()

