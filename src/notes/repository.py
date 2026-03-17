from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.repository import TenantRepository
from core.database.utils import tenant_filter
from notes.models import Note


class NoteRepository(TenantRepository):
    async def list_all(self) -> list[Note]:
        stmt = select(Note).where(tenant_filter(Note, self.workspace_id)).order_by(Note.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_visible_for_member(self, *, user_id: int) -> list[Note]:
        stmt = (
            select(Note)
            .where(
                tenant_filter(Note, self.workspace_id),
                (Note.is_private.is_(False)) | (Note.created_by == user_id),
            )
            .order_by(Note.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get(self, *, note_id: int) -> Note | None:
        stmt = select(Note).where(
            tenant_filter(Note, self.workspace_id),
            Note.id == note_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        created_by: int,
        title: str,
        content: str,
        is_private: bool,
    ) -> Note:
        note = Note(
            workspace_id=self.workspace_id,
            created_by=created_by,
            title=title,
            content=content,
            is_private=is_private,
        )
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def save(self, note: Note) -> Note:
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def delete(self, note: Note) -> None:
        await self.session.delete(note)
        await self.session.commit()

