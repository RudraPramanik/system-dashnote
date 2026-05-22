import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from config import get_settings
from core.database.session import get_session
from core.redis.deps import get_workspace_cache
from core.redis.cache import WorkspaceRedisCache
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from notes.permissions import can_manage_note, can_view_note, can_view_note_fields
from notes.repository import NoteRepository
from notes.schemas import NoteCreate, NoteRead, NoteUpdate
from shared.contracts.indexing import IndexingOperation, IndexingRequest


settings = get_settings()
logger = logging.getLogger(__name__)

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
    request: Request,
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

    # --- AI Slice 1: enqueue embedding job ---
    if settings.ai_enabled:
        try:
            await request.app.state.arq_pool.enqueue_job(
                "embed_note_task",
                request_dict=IndexingRequest(
                    operation=IndexingOperation.UPSERT,
                    note_id=str(note.id),
                    workspace_id=str(ctx.workspace_id),
                    created_by=str(ctx.user_id),
                    is_private=note.is_private,
                    title=note.title,
                    content=data.content,
                ).model_dump(),
            )
        except Exception:
            # Never block the API response for background failures
            logger.warning(
                "Failed to enqueue embedding job",
                extra={"note_id": str(note.id)},
            )

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
    request: Request,
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

    # --- AI Slice 1: enqueue embedding job ---
    if settings.ai_enabled:
        try:
            await request.app.state.arq_pool.enqueue_job(
                "embed_note_task",
                request_dict=IndexingRequest(
                    operation=IndexingOperation.UPSERT,
                    note_id=str(note.id),
                    workspace_id=str(ctx.workspace_id),
                    created_by=str(ctx.user_id),
                    is_private=note.is_private,
                    title=note.title,
                    content=note.content,
                ).model_dump(),
            )
        except Exception:
            # Never block the API response for background failures
            logger.warning(
                "Failed to enqueue embedding job",
                extra={"note_id": str(note.id)},
            )

    return NoteRead.from_orm(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    request: Request,
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

    # --- AI Slice 1: enqueue vector deletion ---
    if settings.ai_enabled:
        try:
            await request.app.state.arq_pool.enqueue_job(
                "embed_note_task",
                request_dict=IndexingRequest(
                    operation=IndexingOperation.DELETE,
                    note_id=str(note_id),
                    workspace_id=str(ctx.workspace_id),
                    created_by=str(ctx.user_id),
                    is_private=False,
                    title="",
                    content="",
                ).model_dump(),
            )
        except Exception:
            logger.warning(
                "Failed to enqueue deletion job",
                extra={"note_id": str(note_id)},
            )

    return None
