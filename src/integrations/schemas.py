"""Pydantic schemas for inbound integrations."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class InboundAttachmentIn(BaseModel):
    filename: str
    content_base64: str
    content_type: str | None = None


class EmailInboundRequest(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=255)
    from_email: str = Field(..., min_length=3, max_length=255)
    subject: str | None = None
    body: str = ""
    attachments: list[InboundAttachmentIn] = Field(default_factory=list)


class AttachmentResult(BaseModel):
    filename: str
    status: str  # attached | rejected
    file_id: UUID | None = None
    reason: str | None = None


class InboundIngestResponse(BaseModel):
    note_id: int
    workspace_id: int
    user_id: int
    title: str
    duplicate: bool = False
    attachments: list[AttachmentResult] = Field(default_factory=list)
    agentic: bool = False


class WhatsAppLinkStartRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=32)


class WhatsAppLinkStartResponse(BaseModel):
    phone: str
    code: str
    message: str = (
        "Confirm with POST /integrations/whatsapp/link/confirm using this code."
    )


class WhatsAppLinkConfirmRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=32)
    code: str = Field(..., min_length=4, max_length=16)


class WhatsAppLinkStatusResponse(BaseModel):
    phone: str
    verified: bool
    wa_id: str | None = None
