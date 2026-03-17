from pydantic import BaseModel


class WorkspaceRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class WorkspaceUpdate(BaseModel):
    name: str

