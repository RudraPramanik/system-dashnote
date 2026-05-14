from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
from core.redis.cache import WorkspaceRedisCache
from core.redis.deps import get_workspace_cache
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.security.permissions import require_roles
from notebooks.repository import NotebookRepository
from notebooks.schemas import NotebookCreate, NotebookRead


router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("/", response_model=list[NotebookRead])
async def list_notebooks(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
):
    """
    List notebooks for the current workspace.
    """
    gen = await cache.read_generation("notebooks")
    key = cache.key_notebooks_list(gen)

    async def load() -> list[dict]:
        repo = NotebookRepository(db, workspace_id=ctx.workspace_id)
        notebooks = await repo.list()
        return [NotebookRead.model_validate(nb).model_dump(mode="json") for nb in notebooks]

    raw = await cache.aside_json(key, load)
    return [NotebookRead.model_validate(item) for item in raw]


@router.post("/", response_model=NotebookRead)
async def create_notebook(
    data: NotebookCreate,
    ctx: RequestContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
    cache: WorkspaceRedisCache = Depends(get_workspace_cache),
):
    """
    Create a notebook in the current workspace.
    Only owner/admin roles are allowed.
    """
    repo = NotebookRepository(db, workspace_id=ctx.workspace_id)
    try:
        notebook = await repo.create(name=data.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await cache.bump_generation("notebooks")
    return NotebookRead.from_orm(notebook)
