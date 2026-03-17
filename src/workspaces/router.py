from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.security.permissions import require_roles
from workspaces.repository import WorkspaceRepository
from workspaces.schemas import WorkspaceRead, WorkspaceUpdate


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/me", response_model=WorkspaceRead)
async def get_my_workspace(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    repo = WorkspaceRepository(db)
    ws = await repo.get(workspace_id=ctx.workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceRead.from_orm(ws)


@router.patch("/me", response_model=WorkspaceRead)
async def rename_my_workspace(
    data: WorkspaceUpdate,
    ctx: RequestContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    repo = WorkspaceRepository(db)
    ws = await repo.get(workspace_id=ctx.workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws.name = data.name
    ws = await repo.save(ws)
    return WorkspaceRead.from_orm(ws)

