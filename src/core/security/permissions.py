from fastapi import Depends, HTTPException, status

from core.security.context import RequestContext
from core.security.dependency import get_current_context


def require_roles(*allowed_roles: str):
    """
    Dependency factory enforcing that the caller has one of the allowed roles.

    Usage:
        @router.post("/invite")
        async def invite_member(
            ctx = Depends(require_roles("owner", "admin")),
        ):
            ...
    """

    async def checker(
        ctx: RequestContext = Depends(get_current_context),
    ) -> RequestContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return ctx

    return checker
