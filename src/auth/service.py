import hashlib
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from auth.models import User, WorkspaceUser
from workspaces.models import Workspace
from auth.security import hash_password, verify_password
from core.redis import get_token_store

PASSWORD_RESET_TTL_SECONDS = 30 * 60
MIN_PASSWORD_LENGTH = 8


class InvalidCurrentPasswordError(Exception):
    """Current password did not match the stored hash."""


class PasswordPolicyError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def register_user(db: AsyncSession, email: str, password: str, workspace_name: str):
    """Create a user, workspace, and membership in a single transaction."""
    user = User(
        email=email,
        password_hash=hash_password(password),
    )
    workspace = Workspace(
        name=workspace_name,
    )

    # Persist user & workspace so they get DB-generated integer IDs
    db.add_all([user, workspace])
    await db.flush()

    membership = WorkspaceUser(
        user_id=user.id,
        tenant_id=workspace.id,
        role="owner",
    )
    db.add(membership)

    await db.commit()

    return user, workspace, membership


async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(
        select(User)
        .options(selectinload(User.workspaces))
        .where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.workspaces))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


def _new_password_hash(new_password: str) -> str:
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError("Password must be at least 8 characters")
    try:
        return hash_password(new_password)
    except ValueError as exc:
        raise PasswordPolicyError(str(exc)) from exc


async def change_password(
    db: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
) -> User:
    user = await get_user_by_id(db, user_id)
    if user is None or not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError
    if current_password == new_password:
        raise PasswordPolicyError("New password must be different")
    user.password_hash = _new_password_hash(new_password)
    await db.commit()
    loaded = await get_user_by_id(db, user.id)
    if loaded is None:
        raise InvalidCurrentPasswordError
    return loaded


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """
    Create a one-time reset token when the email matches a user and Redis can store it.

    Returns the raw token (for the email link) or None when nothing should be sent.
    Never logs the raw token.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    raw = secrets.token_urlsafe(32)
    stored = await get_token_store().store_password_reset_token(
        user_id=user.id,
        digest=hash_reset_token(raw),
        ttl_seconds=PASSWORD_RESET_TTL_SECONDS,
    )
    if not stored:
        return None
    return raw


async def reset_password_with_token(
    db: AsyncSession, raw_token: str, new_password: str
) -> User:
    new_hash = _new_password_hash(new_password)
    user_id = await get_token_store().consume_password_reset_token(
        digest=hash_reset_token(raw_token)
    )
    if user_id is None:
        raise PasswordPolicyError("Invalid or expired reset token")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise PasswordPolicyError("Invalid or expired reset token")
    user.password_hash = new_hash
    await db.commit()
    return user
