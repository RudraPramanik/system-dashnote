from fastapi import HTTPException

from core.security.context import RequestContext
from files.models import File


def can_read(file: File, ctx: RequestContext) -> bool:
    if ctx.role in {"owner", "admin"}:
        return True
    return (not file.is_private) or (file.created_by == ctx.user_id)


def can_modify(file: File, ctx: RequestContext) -> bool:
    if ctx.role in {"owner", "admin"}:
        return True
    return file.created_by == ctx.user_id


def assert_can_read(file: File, ctx: RequestContext) -> None:
    if not can_read(file, ctx):
        raise HTTPException(
            status_code=403,
            detail="No permission to access this file.",
        )


def assert_can_modify(file: File, ctx: RequestContext) -> None:
    if not can_modify(file, ctx):
        raise HTTPException(
            status_code=403,
            detail="No permission to modify this file.",
        )
