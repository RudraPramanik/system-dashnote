from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependency import oauth2_scheme
from auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
)
from auth.service import register_user, authenticate_user
from auth.security import create_access_token, create_refresh_token
from config import settings
from core.database.session import get_db
from core.redis import get_token_store
from core.security.rate_limit import enforce_auth_login_rate_limit


router = APIRouter(prefix="/auth", tags=["auth"])


def _token_ttl_seconds(payload: dict) -> int:
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return 1
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    return max(1, int(exp - now_ts))


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, workspace, membership = await register_user(
            db, data.email, data.password, data.workspace_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    payload = {"sub": str(user.id), "wid": str(workspace.id), "role": membership.role}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    refresh_payload = jwt.decode(
        refresh_token,
        settings.JWT_REFRESH_SECRET,
        algorithms=["HS256"],
    )
    await get_token_store().store_refresh_token(
        user_id=int(refresh_payload["sub"]),
        jti=str(refresh_payload["jti"]),
        ttl_seconds=_token_ttl_seconds(refresh_payload),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_login_rate_limit)],
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # pick default workspace (first membership)
    membership = user.workspaces[0]

    payload = {
        "sub": str(user.id),
        "wid": str(membership.tenant_id),
        "role": membership.role,
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    refresh_payload = jwt.decode(
        refresh_token,
        settings.JWT_REFRESH_SECRET,
        algorithms=["HS256"],
    )
    await get_token_store().store_refresh_token(
        user_id=int(refresh_payload["sub"]),
        jti=str(refresh_payload["jti"]),
        ttl_seconds=_token_ttl_seconds(refresh_payload),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(data: RefreshRequest):
    try:
        payload = jwt.decode(
            data.refresh_token,
            settings.JWT_REFRESH_SECRET,
            algorithms=["HS256"],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    if payload.get("typ") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token type",
        )

    try:
        user_id = int(payload["sub"])
        jti = str(payload["jti"])
        wid = str(payload["wid"])
        role = str(payload["role"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed refresh token",
        ) from exc

    store = get_token_store()
    if not await store.is_refresh_token_active(user_id=user_id, jti=jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or unknown",
        )

    await store.revoke_refresh_token(user_id=user_id, jti=jti)
    next_payload = {"sub": str(user_id), "wid": wid, "role": role}
    access_token = create_access_token(next_payload)
    refresh_token = create_refresh_token(next_payload)
    refresh_payload = jwt.decode(
        refresh_token,
        settings.JWT_REFRESH_SECRET,
        algorithms=["HS256"],
    )
    await store.store_refresh_token(
        user_id=int(refresh_payload["sub"]),
        jti=str(refresh_payload["jti"]),
        ttl_seconds=_token_ttl_seconds(refresh_payload),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    data: LogoutRequest | None = None,
    access_token: str = Depends(oauth2_scheme),
):
    store = get_token_store()
    try:
        access_payload = jwt.decode(
            access_token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        if access_payload.get("typ") != "access":
            raise HTTPException(status_code=401, detail="Invalid access token type")
        await store.blacklist_access_token(
            jti=str(access_payload["jti"]),
            ttl_seconds=_token_ttl_seconds(access_payload),
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    if data and data.refresh_token:
        try:
            refresh_payload = jwt.decode(
                data.refresh_token,
                settings.JWT_REFRESH_SECRET,
                algorithms=["HS256"],
            )
            if refresh_payload.get("typ") == "refresh":
                await store.revoke_refresh_token(
                    user_id=int(refresh_payload["sub"]),
                    jti=str(refresh_payload["jti"]),
                )
        except JWTError:
            pass

    return None