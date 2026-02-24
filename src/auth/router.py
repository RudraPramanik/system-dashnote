from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from auth.service import register_user, authenticate_user
from auth.security import create_access_token, create_refresh_token
from core.database.session import get_db


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, workspace, membership = await register_user(
            db, data.email, data.password, data.workspace_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    payload = {"sub": str(user.id), "wid": str(workspace.id), "role": membership.role}

    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )


@router.post("/login", response_model=TokenResponse)
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

    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )