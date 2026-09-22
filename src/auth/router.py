from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependency import oauth2_scheme
from auth.email import send_password_reset_email
from auth.models import User
from auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
)
from auth.service import (
    register_user,
    authenticate_user,
    change_password,
    request_password_reset,
    reset_password_with_token,
    InvalidCurrentPasswordError,
    PasswordPolicyError,
)
from auth.security import create_access_token, create_refresh_token
from config import settings
from core.database.session import get_db
from core.redis import get_token_store
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.security.rate_limit import (
    enforce_auth_login_rate_limit,
    enforce_auth_forgot_rate_limit,
    enforce_auth_reset_rate_limit,
    enforce_auth_change_password_rate_limit,
)

FORGOT_PASSWORD_MESSAGE = "If an account exists, we sent a reset link."


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


async def _tokens_for_user(user: User) -> TokenResponse:
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
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/change-password",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_change_password_rate_limit)],
)
async def change_password_route(
    data: ChangePasswordRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await change_password(
            db, ctx.user_id, data.current_password, data.new_password
        )
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from exc
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    await get_token_store().revoke_all_refresh_tokens(user_id=user.id)
    return await _tokens_for_user(user)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(enforce_auth_forgot_rate_limit)],
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    raw_token = await request_password_reset(db, data.email)
    if raw_token is not None:
        await send_password_reset_email(to_email=data.email, raw_token=raw_token)
    return ForgotPasswordResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post(
    "/reset-password",
    status_code=204,
    dependencies=[Depends(enforce_auth_reset_rate_limit)],
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await reset_password_with_token(db, data.token, data.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    await get_token_store().revoke_all_refresh_tokens(user_id=user.id)
    return None