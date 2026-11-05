"""Redis key text for AI budgets (Blueprint 9H.4.1).

Stdlib only. Does not read settings, Redis, or a role. Callers pass
trusted user and workspace ids. This module does not enforce a ceiling.
"""
from __future__ import annotations

from datetime import datetime, timezone


def budget_keys(
    user_id: str,
    workspace_id: str,
    when: datetime,
) -> tuple[str | None, str | None, str | None]:
    """Return (user_minute, workspace_day, token) key text, or None per blank id.

    ``when`` must be timezone-aware. Buckets are the UTC epoch minute and the
    UTC calendar date ``YYYYMMDD``.
    """
    if when.tzinfo is None or when.tzinfo.utcoffset(when) is None:
        raise ValueError("budget timestamp must be timezone-aware")

    utc = when.astimezone(timezone.utc)
    epoch_minute = int(utc.timestamp()) // 60
    day = utc.strftime("%Y%m%d")
    user = user_id.strip()
    workspace = workspace_id.strip()

    user_minute = f"ai_req:{user}:{epoch_minute}" if user else None
    workspace_day = f"ai_day:{workspace}:{day}" if workspace else None
    token = f"ai_tok:{workspace}:{day}" if workspace else None
    return user_minute, workspace_day, token
