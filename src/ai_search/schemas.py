from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.retrieval import RetrievalResult


class TestSearchRequest(BaseModel):
    """Query text only — workspace_id comes from JWT context."""

    model_config = ConfigDict(frozen=True)

    query_text: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class TestSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: list[RetrievalResult]
