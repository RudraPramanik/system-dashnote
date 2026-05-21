from pydantic import BaseModel, ConfigDict


class WorkspaceContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: str
    user_id: str
    role: str
