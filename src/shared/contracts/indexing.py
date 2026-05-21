from pydantic import BaseModel, ConfigDict


class IndexingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload_id: str
    workspace_id: str
    target_type: str
    content: str
    metadata: dict


class DeletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload_id: str
    workspace_id: str
    target_type: str


class IndexingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload_id: str
    success: bool
    error_message: str | None
