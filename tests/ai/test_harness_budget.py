"""9H.4.1 AI budget settings and key shapes. No Redis and no live model key."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ai.harness.budget import budget_keys
from ai.harness.context import HarnessContext
from config import Settings
from core.security.rate_limit import _global_limiter

_ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
_BUDGET_ENV = (
    "AI_USER_REQUESTS_PER_MINUTE",
    "AI_WORKSPACE_REQUESTS_PER_DAY",
    "AI_TOKEN_BUDGET_PER_DAY",
)


def _settings(**overrides: object) -> Settings:
    return Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        JWT_SECRET="test-secret",
        _env_file=None,
        **overrides,
    )


def test_budget_defaults_are_below_the_global_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _BUDGET_ENV:
        monkeypatch.delenv(name, raising=False)
    loaded = _settings()
    assert loaded.AI_USER_REQUESTS_PER_MINUTE == 20
    assert loaded.AI_USER_REQUESTS_PER_MINUTE < 100
    assert loaded.AI_WORKSPACE_REQUESTS_PER_DAY == 200
    assert loaded.AI_TOKEN_BUDGET_PER_DAY == 0
    example = _ENV_EXAMPLE.read_text(encoding="utf-8")
    for name in _BUDGET_ENV:
        assert name in example
    assert _global_limiter.limit == 100
    assert _global_limiter.window_seconds == 60


def test_budget_settings_load_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_USER_REQUESTS_PER_MINUTE", "40")
    monkeypatch.setenv("AI_WORKSPACE_REQUESTS_PER_DAY", "15")
    monkeypatch.setenv("AI_TOKEN_BUDGET_PER_DAY", "1000")
    loaded = _settings()
    assert loaded.AI_USER_REQUESTS_PER_MINUTE == 40
    assert loaded.AI_WORKSPACE_REQUESTS_PER_DAY == 15
    assert loaded.AI_TOKEN_BUDGET_PER_DAY == 1000


def test_distinct_identities_share_utc_buckets_and_omit_role() -> None:
    # 2026-01-01 02:30 UTC is still 2025-12-31 in a zone eight hours behind UTC.
    when = datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)
    behind = timezone(timedelta(hours=-8))
    assert when.astimezone(behind).strftime("%Y%m%d") == "20251231"

    params = inspect.signature(budget_keys).parameters
    assert "role" not in params
    assert list(params) == ["user_id", "workspace_id", "when"]

    first = budget_keys("user-1", "ws-1", when)
    second = budget_keys("user-2", "ws-2", when)
    epoch_minute = int(when.timestamp()) // 60
    assert first == (
        f"ai_req:user-1:{epoch_minute}",
        "ai_day:ws-1:20260101",
        "ai_tok:ws-1:20260101",
    )
    assert second[0] != first[0]
    assert second[1] != first[1]
    assert second[0].endswith(f":{epoch_minute}")
    assert second[1].endswith(":20260101")
    assert second[2] == "ai_tok:ws-2:20260101"
    for key in (*first, *second):
        assert key is not None
        assert "owner" not in key
        assert "admin" not in key
        assert "member" not in key

    same_instant = when.astimezone(behind)
    assert budget_keys("user-1", "ws-1", same_instant) == first


def test_blank_identity_does_not_share_a_bucket() -> None:
    when = datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)
    user_blank = budget_keys("  ", "ws-1", when)
    workspace_blank = budget_keys("user-1", "", when)
    assert user_blank[0] is None
    assert user_blank[1] == "ai_day:ws-1:20260101"
    assert user_blank[2] == "ai_tok:ws-1:20260101"
    assert workspace_blank[0] == f"ai_req:user-1:{int(when.timestamp()) // 60}"
    assert workspace_blank[1] is None
    assert workspace_blank[2] is None
    rendered = " ".join(key for key in (*user_blank, *workspace_blank) if key)
    assert "anonymous" not in rendered
    assert "ai_req::" not in rendered
    assert "ai_day::" not in rendered
    assert "ai_tok::" not in rendered


def test_naive_datetime_is_rejected_and_remaining_budget_stays_unset() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        budget_keys("user-1", "ws-1", datetime(2026, 1, 1, 2, 30))
    context = HarnessContext(workspace_id="ws-1", user_id="user-1", role="owner")
    assert context.remaining_budget is None
