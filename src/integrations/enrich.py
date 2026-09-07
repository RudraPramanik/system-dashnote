"""Optional agentic title/tag enrichment for inbound dump content."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from config import get_settings

logger = logging.getLogger(__name__)


async def enrich_title_and_tags(
    *,
    subject: str | None,
    body: str,
    workspace_id: int,
) -> tuple[str, list[str]] | None:
    """
    Return (title, tags) when agentic inbound is enabled and LLM succeeds.
    Never changes workspace_id — caller already resolved tenancy.
    """
    settings = get_settings()
    if not settings.INBOUND_AGENTIC_ENABLED:
        return None
    if not settings.ai_enabled:
        return None

    prompt = (
        "Given an inbound message, propose a short note title (max 80 chars) "
        "and up to 5 lowercase tags. Reply JSON only: "
        '{"title":"...","tags":["..."]}.\n\n'
        f"Subject: {subject or ''}\n"
        f"Body:\n{(body or '')[:4000]}\n"
        f"(workspace_id={workspace_id} — do not invent another workspace)\n"
    )

    timeout = float(settings.INBOUND_AGENTIC_TIMEOUT_SECONDS)

    async def _call() -> tuple[str, list[str]] | None:
        try:
            from shared.llm.fallback import acompletion_with_fallback

            resp = await acompletion_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.0,
            )
            text = ""
            if hasattr(resp, "choices") and resp.choices:
                text = (resp.choices[0].message.content or "").strip()
            else:
                text = str(resp)
            return _parse_enrichment(text, subject=subject, body=body)
        except Exception as e:
            logger.warning(
                "Inbound agentic enrichment failed",
                extra={"error": str(e)[:240], "workspace_id": workspace_id},
            )
            return None

    try:
        return await asyncio.wait_for(_call(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(
            "Inbound agentic enrichment timed out",
            extra={"workspace_id": workspace_id, "timeout": timeout},
        )
        return None


def _parse_enrichment(
    text: str,
    *,
    subject: str | None,
    body: str,
) -> tuple[str, list[str]] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    title = str(data.get("title") or "").strip()
    if not title:
        title = (subject or "").strip() or _fallback_title(body)
    title = title[:255]
    tags_raw = data.get("tags") or []
    tags: list[str] = []
    if isinstance(tags_raw, list):
        for t in tags_raw[:5]:
            s = str(t).strip().lower()
            if s:
                tags.append(s[:64])
    return title, tags


def dump_title(subject: str | None, body: str) -> str:
    title = (subject or "").strip()
    if title:
        return title[:255]
    return _fallback_title(body)


def _fallback_title(body: str) -> str:
    line = (body or "").strip().splitlines()[0] if (body or "").strip() else ""
    if line:
        return line[:80]
    return "Inbound note"
