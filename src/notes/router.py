from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from notes.permissions import can_manage_note, can_view_note
from notes.repository import NoteRepository
from notes.schemas import NoteCreate, NoteRead, NoteUpdate


router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[NoteRead])
async def list_notes(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    if ctx.role in {"owner", "admin"}:
        notes = await repo.list_all()
    else:
        notes = await repo.list_visible_for_member(user_id=ctx.user_id)
    return [NoteRead.from_orm(n) for n in notes]


@router.post("/", response_model=NoteRead)
async def create_note(
    data: NoteCreate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.create(
        created_by=ctx.user_id,
        title=data.title,
        content=data.content,
        is_private=data.is_private,
    )
    return NoteRead.from_orm(note)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.get(note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not can_view_note(ctx, note):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return NoteRead.from_orm(note)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: int,
    data: NoteUpdate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.get(note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not can_manage_note(ctx, note):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if data.title is not None:
        note.title = data.title
    if data.content is not None:
        note.content = data.content
    if data.is_private is not None:
        note.is_private = data.is_private

    note = await repo.save(note)
    return NoteRead.from_orm(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.get(note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not can_manage_note(ctx, note):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    await repo.delete(note)
    return None

