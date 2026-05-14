from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError

from config import settings
from core.redis import get_token_store
from core.security.context import RequestContext
from auth.dependency import oauth2_scheme, oauth2_scheme_optional


async def _context_from_access_token(token: str) -> RequestContext:
    """
    Decode a bearer access token into RequestContext.

    Used by `get_current_context` and optional helpers (e.g. rate limiting identity).
    """

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        if payload.get("typ") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token type",
            )
        if await get_token_store().is_access_token_blacklisted(jti=str(payload["jti"])):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        return RequestContext(
            user_id=int(payload["sub"]),
            workspace_id=int(payload["wid"]),
            role=payload["role"],
        )
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_context(
    token: str = Depends(oauth2_scheme),
) -> RequestContext:
    """
    Decode JWT and build a RequestContext.

    Tokens are created in `auth.router` with:
      sub: user id
      wid: workspace id
      role: role within that workspace
    """

    return await _context_from_access_token(token)


async def get_optional_current_context(
    token: str | None = Depends(oauth2_scheme_optional),
) -> RequestContext | None:
    """Same validation as `get_current_context`, but returns None when no bearer token."""

    if token is None:
        return None
    try:
        return await _context_from_access_token(token)
    except HTTPException:
        return None
