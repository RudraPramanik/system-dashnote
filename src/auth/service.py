from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth.models import User,WorkspaceUser
from workspaces.models import Workspace
from auth.security import hash_password, verify_password
from uuid import uuid4


async def register_user(db:AsyncSession, email:str, password: str, workspace_name:str):
    user = User(
        id=uuid4(),
        email= email,
        hashed_password = hash_password(password),
    )
    workspace = Workspace(
        id= uuid4(),
        name = workspace_name,
    )
    membership = WorkspaceUser(
        user_id = user.id,
        workspace_id = workspace.id,
        role = "owner",
    )

    db.add_all([user, workspace, membership])
    await db.commit()

    return user, workspace, membership

async def authenticate_user(db:AsyncSession, email:str, password:str):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
