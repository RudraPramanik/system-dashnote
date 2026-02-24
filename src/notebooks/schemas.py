from pydantic import BaseModel


class NotebookCreate(BaseModel):
    name: str


class NotebookRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

