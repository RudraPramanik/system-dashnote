from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
from core.database.utils import tenant_filter
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.security.permissions import require_roles
from core.storage.client import StorageBackend, get_storage
from core.storage.utils import (
    detect_mime_type,
    generate_storage_key,
    safe_filename,
    validate_file,
)
from files import repository as files_repo
from files.models import File as FileModel
from files.permissions import assert_can_modify, assert_can_read
from files.schemas import FileCreate, FileListResponse, FileResponse, FileUpdate
from notes.permissions import can_manage_note
from notes.repository import NoteRepository


router = APIRouter()


def _to_response(file: FileModel, storage: StorageBackend) -> FileResponse:
    url = storage.presigned_url(file.storage_key) or f"/files/{file.id}/download"
    base = FileResponse.model_validate(file)
    return base.model_copy(update={"download_url": url})


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    is_private: bool = Form(True),
    description: str = Form(""),
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    data = await file.read()
    detected = detect_mime_type(data)
    validate_file(file.filename or "", len(data), detected)
    safe_name = safe_filename(file.filename or "upload")
    key = generate_storage_key(str(ctx.workspace_id), safe_name)
    await storage.upload(key, data, detected)

    desc = description.strip() or None
    record = await files_repo.create(
        session,
        ctx.workspace_id,
        ctx.user_id,
        FileCreate(
            name=safe_name,
            mime_type=detected,
            size_bytes=len(data),
            is_private=is_private,
            description=desc,
        ),
        storage_key=key,
    )
    return _to_response(record, storage)


@router.get("/", response_model=FileListResponse)
async def list_files(
    skip: int = 0,
    limit: int = 20,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    rows, total = await files_repo.list_files(
        session,
        ctx.workspace_id,
        ctx.user_id,
        ctx.role,
        skip,
        limit,
    )
    return FileListResponse(
        items=[_to_response(f, storage) for f in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/admin/all", response_model=FileListResponse)
async def list_all_files_admin(
    skip: int = 0,
    limit: int = 20,
    ctx: RequestContext = Depends(require_roles("owner", "admin")),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    filt = tenant_filter(FileModel, ctx.workspace_id)
    count_stmt = select(func.count()).select_from(FileModel).where(filt)
    total_result = await session.execute(count_stmt)
    total = int(total_result.scalar_one())

    list_stmt = (
        select(FileModel)
        .where(filt)
        .order_by(FileModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(list_stmt)
    rows = list(result.scalars().all())
    return FileListResponse(
        items=[_to_response(f, storage) for f in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: UUID,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    row = await files_repo.get_by_id(session, ctx.workspace_id, file_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    assert_can_read(row, ctx)
    return _to_response(row, storage)


@router.get("/{file_id}/download")
async def download_file(
    file_id: UUID,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    row = await files_repo.get_by_id(session, ctx.workspace_id, file_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    assert_can_read(row, ctx)
    raw = await storage.download(row.storage_key)
    return StreamingResponse(
        iter([raw]),
        media_type=row.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{row.name}"',
        },
    )


@router.patch("/{file_id}", response_model=FileResponse)
async def patch_file(
    file_id: UUID,
    data: FileUpdate,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    row = await files_repo.get_by_id(session, ctx.workspace_id, file_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    assert_can_modify(row, ctx)
    updated = await files_repo.update(session, ctx.workspace_id, file_id, data)
    assert updated is not None
    return _to_response(updated, storage)


@router.delete("/{file_id}")
async def delete_file(
    file_id: UUID,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    storage: StorageBackend = Depends(get_storage),
):
    row = await files_repo.get_by_id(session, ctx.workspace_id, file_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    assert_can_modify(row, ctx)
    await storage.delete(row.storage_key)
    await files_repo.delete(session, ctx.workspace_id, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{file_id}/attach/{note_id}")
async def attach_file_to_note(
    file_id: UUID,
    note_id: int,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
    _storage: StorageBackend = Depends(get_storage),
):
    file_row = await files_repo.get_by_id(session, ctx.workspace_id, file_id)
    if file_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    assert_can_modify(file_row, ctx)

    notes_repo = NoteRepository(session, workspace_id=ctx.workspace_id)
    note = await notes_repo.get(note_id=note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if not can_manage_note(ctx, note):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    await files_repo.link_to_note(session, ctx.workspace_id, note_id, file_id)
    return {"attached": True}
