"""Pytest bootstrap: stub optional native deps and env for Settings."""

import os
import sys
import types

import pytest


def _ensure_magic_stub() -> None:
    """Allow importing `core.storage.utils` without system libmagic (e.g. Windows CI)."""
    if "magic" in sys.modules:
        return
    mod = types.ModuleType("magic")

    def from_buffer(data: bytes, mime: bool = False) -> str:
        return "application/octet-stream"

    mod.from_buffer = from_buffer
    sys.modules["magic"] = mod


_ensure_magic_stub()

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://dashuser:dashpass@127.0.0.1:5432/dashnotes",
)
os.environ.setdefault("JWT_SECRET", "pytest-jwt-secret-not-for-production")


@pytest.fixture(autouse=True)
def _reset_shared_redis_after_test() -> None:
    yield
    from core.redis.client import reset_async_redis_client

    reset_async_redis_client()
