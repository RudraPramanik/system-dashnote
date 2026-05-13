from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.associations import note_attachments
from core.database.utils import tenant_filter
from files.models import File
from files.schemas import FileCreate, FileUpdate
from notes.models import Note


async def get_by_id(
    session: AsyncSession,
    workspace_id: int,
    file_id: UUID,
) -> File | None:
    stmt = select(File).where(
        tenant_filter(File, workspace_id),
        File.id == file_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_files(
    session: AsyncSession,
    workspace_id: int,
    user_id: int,
    role: str,
    skip: int,
    limit: int,
) -> tuple[list[File], int]:
    visibility = tenant_filter(File, workspace_id)
    if role not in {"owner", "admin"}:
        visibility = visibility & (
            (File.is_private.is_(False)) | (File.created_by == user_id)
        )

    count_stmt = select(func.count()).select_from(File).where(visibility)
    total_result = await session.execute(count_stmt)
    total = int(total_result.scalar_one())

    list_stmt = (
        select(File)
        .where(visibility)
        .order_by(File.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = await session.execute(list_stmt)
    return list(rows.scalars().all()), total


async def create(
    session: AsyncSession,
    workspace_id: int,
    user_id: int,
    data: FileCreate,
    storage_key: str,
) -> File:
    row = File(
        workspace_id=workspace_id,
        created_by=user_id,
        name=data.name,
        mime_type=data.mime_type,
        size_bytes=data.size_bytes,
        is_private=data.is_private,
        description=data.description,
        storage_key=storage_key,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update(
    session: AsyncSession,
    workspace_id: int,
    file_id: UUID,
    data: FileUpdate,
) -> File | None:
    row = await get_by_id(session, workspace_id, file_id)
    if row is None:
        return None

    if data.name is not None:
        row.name = data.name
    if data.is_private is not None:
        row.is_private = data.is_private
    if data.description is not None:
        row.description = data.description

    await session.commit()
    await session.refresh(row)
    return row


async def delete(session: AsyncSession, workspace_id: int, file_id: UUID) -> bool:
    row = await get_by_id(session, workspace_id, file_id)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True


async def link_to_note(
    session: AsyncSession,
    workspace_id: int,
    note_id: int,
    file_id: UUID,
) -> None:
    stmt_file = select(File).where(File.id == file_id)
    file_result = await session.execute(stmt_file)
    file_row = file_result.scalar_one_or_none()
    if file_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    if file_row.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File is not in this workspace.",
        )

    stmt_note = select(Note).where(Note.id == note_id)
    note_result = await session.execute(stmt_note)
    note_row = note_result.scalar_one_or_none()
    if note_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found.",
        )
    if note_row.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Note is not in this workspace.",
        )

    stmt = insert(note_attachments).values(
        note_id=note_id,
        file_id=file_id,
        workspace_id=workspace_id,
    ).on_conflict_do_nothing(
        index_elements=[note_attachments.c.note_id, note_attachments.c.file_id],
    )
    await session.execute(stmt)
    await session.commit()
