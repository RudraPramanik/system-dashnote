"""Outbound password-reset mail via Resend. Soft: missing config never raises."""

from __future__ import annotations

import asyncio
import logging

from config import settings

logger = logging.getLogger(__name__)


def _send_resend_email(*, to_email: str, reset_url: str) -> str | None:
    try:
        import resend
    except ImportError:
        logger.warning("resend package not installed; skip password-reset email")
        return None

    resend.api_key = settings.RESEND_API_KEY
    params = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your DashNotes password",
        "html": (
            "<p>We received a request to reset your password.</p>"
            f'<p><a href="{reset_url}">Choose a new password</a></p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        ),
        "text": f"Reset your DashNotes password: {reset_url}",
    }
    email = resend.Emails.send(params)
    if isinstance(email, dict):
        return email.get("id")
    return getattr(email, "id", None)


async def send_password_reset_email(*, to_email: str, raw_token: str) -> None:
    """Send a reset link. Never raises. Never logs the raw token."""
    api_key = (settings.RESEND_API_KEY or "").strip()
    from_email = (settings.RESEND_FROM_EMAIL or "").strip()
    frontend = (settings.FRONTEND_PUBLIC_URL or "").strip().rstrip("/")
    if not api_key or not from_email or not frontend:
        logger.warning("Password reset email skipped: Resend or FRONTEND_PUBLIC_URL unset")
        return

    reset_url = f"{frontend}/auth/reset?token={raw_token}"
    try:
        email_id = await asyncio.to_thread(
            _send_resend_email, to_email=to_email, reset_url=reset_url
        )
        if email_id:
            logger.info("Password reset email accepted by Resend id=%s", email_id)
    except Exception:
        logger.exception("Password reset email failed")
