from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth.models import User, WorkspaceUser
from workspaces.models import Workspace
from auth.security import hash_password, verify_password


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
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
