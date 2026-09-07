"""WhatsApp Cloud API signature + payload helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any


def verify_meta_signature(*, app_secret: str, body: bytes, header_value: str | None) -> bool:
    if not app_secret or not header_value:
        return False
    provided = header_value.removeprefix("sha256=").strip()
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def generate_link_code(length: int = 6) -> str:
    # Numeric code for easy WhatsApp / settings UX
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"


def extract_text_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """
    Normalize Meta webhook payload into [{message_id, from, text}].
    Media-only messages are returned with empty text and media=true marker via text=''.
    """
    out: list[dict[str, str]] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                mid = str(msg.get("id") or "")
                sender = str(msg.get("from") or "")
                msg_type = str(msg.get("type") or "")
                text = ""
                if msg_type == "text":
                    text = str((msg.get("text") or {}).get("body") or "")
                out.append(
                    {
                        "message_id": mid,
                        "from": sender,
                        "text": text,
                        "type": msg_type,
                    }
                )
    return out
