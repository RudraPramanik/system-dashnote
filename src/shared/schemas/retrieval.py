from pydantic import BaseModel, ConfigDict

from shared.schemas.note import NoteChunk


class HybridSearchQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_text: str
    workspace_id: str
    limit: int = 5


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float
    content_chunk: NoteChunk
    metadata: dict
