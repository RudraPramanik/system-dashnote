"""
Configure LiteLLM provider credentials from Settings.

Call once at API lifespan startup and ARQ worker startup so all
litellm.acompletion / aembedding paths see the same env vars.
"""
from __future__ import annotations

import os

from config import Settings


def configure_litellm_env(settings: Settings) -> None:
    """Push provider API keys into os.environ for LiteLLM (setdefault — never overwrite)."""
    if settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if settings.GEMINI_API_KEY:
        os.environ.setdefault("GEMINI_API_KEY", settings.GEMINI_API_KEY)

    nvidia_key = settings.effective_nvidia_nim_api_key
    if nvidia_key:
        os.environ.setdefault("NVIDIA_NIM_API_KEY", nvidia_key)

    if settings.NVIDIA_NIM_API_BASE:
        os.environ.setdefault("NVIDIA_NIM_API_BASE", settings.NVIDIA_NIM_API_BASE)
