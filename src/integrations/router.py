"""HTTP routes for inbound email / WhatsApp integrations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from integrations.auth import require_inbound_api_key, require_inbound_hmac_if_configured
from integrations.identity import (
    normalize_phone,
    resolve_email_sender,
    resolve_whatsapp_sender,
)
from integrations.ingest import CHANNEL_WHATSAPP, ingest_email, ingest_text_message
from integrations.models import WhatsAppIdentityLink
from integrations.schemas import (
    EmailInboundRequest,
    InboundIngestResponse,
    WhatsAppLinkConfirmRequest,
    WhatsAppLinkStartRequest,
    WhatsAppLinkStartResponse,
    WhatsAppLinkStatusResponse,
)
from integrations.whatsapp import (
    extract_text_messages,
    generate_link_code,
    verify_meta_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post(
    "/inbound/email",
    response_model=InboundIngestResponse,
    dependencies=[Depends(require_inbound_api_key), Depends(require_inbound_hmac_if_configured)],
)
async def inbound_email(
    request: Request,
    payload: EmailInboundRequest,
    db: AsyncSession = Depends(get_session),
):
    identity = await resolve_email_sender(db, payload.from_email)
    return await ingest_email(request, db, payload, identity)


@router.post("/whatsapp/link/start", response_model=WhatsAppLinkStartResponse)
async def whatsapp_link_start(
    body: WhatsAppLinkStartRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    phone = normalize_phone(body.phone)
    code = generate_link_code()
    stmt = select(WhatsAppIdentityLink).where(WhatsAppIdentityLink.phone == phone)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link is not None and link.user_id != ctx.user_id and link.verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone already linked to another user.",
        )
    if link is None:
        link = WhatsAppIdentityLink(user_id=ctx.user_id, phone=phone)
        db.add(link)
    link.user_id = ctx.user_id
    link.phone = phone
    link.pending_code = code
    link.verified_at = None
    await db.commit()
    return WhatsAppLinkStartResponse(phone=phone, code=code)


@router.post("/whatsapp/link/confirm", response_model=WhatsAppLinkStatusResponse)
async def whatsapp_link_confirm(
    body: WhatsAppLinkConfirmRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    phone = normalize_phone(body.phone)
    stmt = select(WhatsAppIdentityLink).where(
        WhatsAppIdentityLink.phone == phone,
        WhatsAppIdentityLink.user_id == ctx.user_id,
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link is None or not link.pending_code or link.pending_code != body.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid link code.",
        )
    link.verified_at = datetime.now(timezone.utc)
    link.pending_code = None
    link.wa_id = phone.lstrip("+")
    await db.commit()
    return WhatsAppLinkStatusResponse(phone=phone, verified=True, wa_id=link.wa_id)


@router.delete("/whatsapp/link", status_code=status.HTTP_204_NO_CONTENT)
async def whatsapp_link_unlink(
    phone: str = Query(..., min_length=5),
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    normalized = normalize_phone(phone)
    stmt = select(WhatsAppIdentityLink).where(
        WhatsAppIdentityLink.phone == normalized,
        WhatsAppIdentityLink.user_id == ctx.user_id,
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")
    await db.delete(link)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/whatsapp/webhook")
async def whatsapp_webhook_verify(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    settings = get_settings()
    expected = (settings.WHATSAPP_VERIFY_TOKEN or "").strip()
    if hub_mode == "subscribe" and expected and hub_verify_token == expected:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed.")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook_receive(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    app_secret = (settings.WHATSAPP_APP_SECRET or "").strip()
    if not app_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp webhook is not configured.",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_meta_signature(
        app_secret=app_secret,
        body=body,
        header_value=signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WhatsApp signature.",
        )

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON.")

    results = []
    for msg in extract_text_messages(payload):
        mid = msg.get("message_id") or ""
        sender = msg.get("from") or ""
        text = msg.get("text") or ""
        msg_type = msg.get("type") or ""
        if not mid or not sender:
            continue

        # Media-only / non-text: acknowledge without empty note
        if msg_type and msg_type != "text":
            results.append(
                {
                    "message_id": mid,
                    "status": "rejected",
                    "reason": "Text-first MVP; media not stored under current file policy.",
                }
            )
            continue
        if not text.strip():
            results.append(
                {
                    "message_id": mid,
                    "status": "rejected",
                    "reason": "Empty text; no note created.",
                }
            )
            continue

        try:
            identity = await resolve_whatsapp_sender(db, sender)
        except HTTPException as e:
            results.append(
                {
                    "message_id": mid,
                    "status": "rejected",
                    "reason": str(e.detail),
                }
            )
            continue

        ingest = await ingest_text_message(
            request,
            db,
            channel=CHANNEL_WHATSAPP,
            provider_message_id=mid,
            identity=identity,
            subject=None,
            body=text,
            attachments=None,
        )
        results.append(
            {
                "message_id": mid,
                "status": "ok",
                "note_id": ingest.note_id,
                "duplicate": ingest.duplicate,
            }
        )

    return {"results": results}
