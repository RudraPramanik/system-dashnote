"""
Compatibility shim for configuration.

The actual settings live in `src/config.py`, but many modules import:

    from config import settings

To make this work both when running the app via `fastapi dev src/main.py`
and when running tests/tools from the project root, we re-export `settings`
from the real module here.
"""

from src.config import get_settings, settings  # type: ignore[import-untyped]

__all__ = ["get_settings", "settings"]

