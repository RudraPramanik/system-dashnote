from pydantic import BaseModel, ConfigDict


class NoteChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    note_id: str
    workspace_id: str
    text: str
    index: int


class NoteReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    note_id: str
    title: str
    match_score: float
