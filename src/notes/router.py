from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
from core.redis.deps import get_workspace_cache
from core.redis.cache import WorkspaceRedisCache
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from notes.permissions import can_manage_note, can_view_note, can_view_note_fields
from notes.repository import NoteRepository
from notes.schemas import NoteCreate, NoteRead, NoteUpdate


router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[NoteRead])
async def list_notes(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
):
    gen = await cache.read_generation("notes")
    key = cache.key_notes_list(gen)

    async def load() -> list[dict]:
        repo = NoteRepository(db, workspace_id=ctx.workspace_id)
        if ctx.role in {"owner", "admin"}:
            notes = await repo.list_all()
        else:
            notes = await repo.list_visible_for_member(user_id=ctx.user_id)
        return [NoteRead.model_validate(n).model_dump(mode="json") for n in notes]

    raw = await cache.aside_json(key, load)
    return [NoteRead.model_validate(item) for item in raw]


@router.post("/", response_model=NoteRead)
async def create_note(
    data: NoteCreate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.create(
        created_by=ctx.user_id,
        title=data.title,
        content=data.content,
        is_private=data.is_private,
    )
    await cache.bump_generation("notes")
    return NoteRead.from_orm(note)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
):
    gen = await cache.read_generation("notes")
    key = cache.key_note_detail(gen, note_id)
    cached = await cache.get_json(key)
    if isinstance(cached, dict):
        try:
            if can_view_note_fields(
                ctx,
                is_private=bool(cached["is_private"]),
                created_by=int(cached["created_by"]),
            ):
                return NoteRead.model_validate(cached)
        except (KeyError, TypeError, ValueError):
            pass

    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.get(note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not can_view_note(ctx, note):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    body = NoteRead.model_validate(note).model_dump(mode="json")
    await cache.set_json(key, body)
    return NoteRead.model_validate(body)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: int,
    data: NoteUpdate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
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
    await cache.bump_generation("notes")
    return NoteRead.from_orm(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
):
    repo = NoteRepository(db, workspace_id=ctx.workspace_id)
    note = await repo.get(note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not can_manage_note(ctx, note):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    await repo.delete(note)
    await cache.bump_generation("notes")
    return None
