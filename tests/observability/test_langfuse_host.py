"""CI-safe Langfuse host alias + enablement (no Langfuse network)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from config import Settings
from observability.langfuse_client import get_langfuse_client


def _settings(
    *,
    public_key: str = "",
    secret_key: str = "",
    host: str = "",
    base_url: str = "",
) -> Settings:
    return Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        JWT_SECRET="test-secret",
        LANGFUSE_PUBLIC_KEY=public_key,
        LANGFUSE_SECRET_KEY=secret_key,
        LANGFUSE_HOST=host,
        LANGFUSE_BASE_URL=base_url,
    )


def test_disabled_when_keys_missing() -> None:
    s = _settings()
    assert s.langfuse_enabled is False
    assert s.effective_langfuse_host == "https://cloud.langfuse.com"


def test_enabled_when_both_keys_set() -> None:
    s = _settings(public_key="pk-lf-test", secret_key="sk-lf-test")
    assert s.langfuse_enabled is True


def test_host_wins_over_base_url_alias() -> None:
    s = _settings(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        host="https://cloud.langfuse.com",
        base_url="https://us.cloud.langfuse.com",
    )
    assert s.effective_langfuse_host == "https://cloud.langfuse.com"


def test_base_url_alias_when_host_blank() -> None:
    s = _settings(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        host="",
        base_url="https://us.cloud.langfuse.com",
    )
    assert s.langfuse_enabled is True
    assert s.effective_langfuse_host == "https://us.cloud.langfuse.com"


def test_client_none_when_keys_missing() -> None:
    settings = _settings()
    with (
        patch("observability.langfuse_client.get_settings", return_value=settings),
        patch("observability.langfuse_client._initialized", False),
        patch("observability.langfuse_client._client", None),
    ):
        assert get_langfuse_client() is None


def test_client_uses_effective_host_no_network() -> None:
    settings = _settings(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        host="",
        base_url="https://us.cloud.langfuse.com",
    )
    fake = MagicMock()
    with (
        patch("observability.langfuse_client.get_settings", return_value=settings),
        patch("observability.langfuse_client._initialized", False),
        patch("observability.langfuse_client._client", None),
        patch("langfuse.Langfuse", return_value=fake) as ctor,
    ):
        client = get_langfuse_client()
    assert client is fake
    ctor.assert_called_once()
    kwargs = ctor.call_args.kwargs
    assert kwargs["host"] == "https://us.cloud.langfuse.com"
    assert kwargs["public_key"] == "pk-lf-test"


def test_score_by_trace_id_uses_v3_create_score() -> None:
    from observability.tracing import score_by_trace_id

    fake = MagicMock()
    fake.score = None
    fake.create_score = MagicMock()
    fake.flush = MagicMock()
    with patch("observability.tracing.get_langfuse_client", return_value=fake):
        ok = score_by_trace_id("tr-1", name="user_feedback", value=1, comment="thumbs=up")
    assert ok is True
    fake.create_score.assert_called_once()
    kwargs = fake.create_score.call_args.kwargs
    assert kwargs["trace_id"] == "tr-1"
    assert kwargs["name"] == "user_feedback"
    assert kwargs["value"] == 1.0
