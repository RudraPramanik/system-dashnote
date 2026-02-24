from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError

from config import settings
from core.security.context import RequestContext
from auth.dependency import oauth2_scheme


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

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
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
