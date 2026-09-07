"""Inbound service authentication (API key / optional HMAC)."""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from config import get_settings


def _constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def require_inbound_api_key(
    x_inbound_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Reject missing/invalid inbound API keys without side effects."""
    settings = get_settings()
    expected = (settings.INBOUND_API_KEY or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inbound integrations are not configured.",
        )
    if not x_inbound_api_key or not _constant_time_equals(x_inbound_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inbound credentials.",
        )


async def require_inbound_hmac_if_configured(
    request: Request,
    x_inbound_signature: Annotated[str | None, Header()] = None,
) -> None:
    """
    Optional body HMAC (hex digest of raw body with INBOUND_HMAC_SECRET).
    Skipped when INBOUND_HMAC_SECRET is empty.
    """
    settings = get_settings()
    secret = (settings.INBOUND_HMAC_SECRET or "").strip()
    if not secret:
        return
    if not x_inbound_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing inbound signature.",
        )
    body = await request.body()
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = x_inbound_signature.removeprefix("sha256=").strip()
    if not _constant_time_equals(provided, digest):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inbound signature.",
        )


InboundAuth = Annotated[None, Depends(require_inbound_api_key)]
