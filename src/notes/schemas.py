from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str
    is_private: bool = False


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_private: bool | None = None


class NoteRead(BaseModel):
    id: int
    title: str
    content: str
    is_private: bool
    created_by: int

    class Config:
        from_attributes = True

