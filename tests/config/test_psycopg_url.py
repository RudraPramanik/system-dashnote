"""DATABASE_URL adaptation for LangGraph psycopg checkpointer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from config import adapt_database_url_for_psycopg


def test_strips_asyncpg_driver():
    url = adapt_database_url_for_psycopg(
        "postgresql+asyncpg://user:pass@db.example:5432/app"
    )
    assert url.startswith("postgresql://user:pass@db.example:5432/app")
    assert "+asyncpg" not in url


def test_maps_ssl_require_to_sslmode():
    url = adapt_database_url_for_psycopg(
        "postgresql+asyncpg://u:p@h:5432/db?ssl=require"
    )
    assert "sslmode=require" in url
    assert "ssl=require" not in url


def test_preserves_existing_sslmode():
    url = adapt_database_url_for_psycopg(
        "postgresql+asyncpg://u:p@h:5432/db?sslmode=verify-full"
    )
    assert "sslmode=verify-full" in url


def test_supabase_defaults_sslmode_require():
    url = adapt_database_url_for_psycopg(
        "postgresql+asyncpg://u:p@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"
    )
    assert "sslmode=require" in url


def test_local_host_no_forced_ssl():
    url = adapt_database_url_for_psycopg(
        "postgresql+asyncpg://postgres:postgres@db:5432/dashnote"
    )
    assert "sslmode" not in url
