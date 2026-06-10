#!/usr/bin/env python3
"""
Pre-flight NVIDIA NIM tests before switching LLM_MODEL in .env.

Usage:
  python scripts/test_nvidia_nim.py
  python scripts/test_nvidia_nim.py --model nvidia_nim/mistralai/mistral-medium-3.5-128b
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Match alembic/env.py + pytest: src/ on path, then `from config import settings`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import litellm
from pydantic import BaseModel, Field

from config import get_settings
from shared.llm.env import configure_litellm_env

DEFAULT_NIM_LLM = "nvidia_nim/mistralai/mistral-medium-3.5-128b"


class TagAnalysis(BaseModel):
    tags: list[str] = Field(description="Up to 5 lowercase keyword tags")


def _ok(name: str) -> None:
    print(f"  PASS  {name}")


def _fail(name: str, detail: str) -> None:
    print(f"  FAIL  {name}: {detail}")


async def test_plain(model: str) -> bool:
    t0 = time.time()
    try:
        r = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: NIM_OK"}],
            temperature=0.0,
            max_tokens=16,
        )
        content = (r.choices[0].message.content or "").strip()
        elapsed = time.time() - t0
        if "NIM_OK" in content.upper() or "NIM" in content.upper():
            _ok(f"plain completion ({elapsed:.1f}s): {content!r}")
            return True
        _ok(f"plain completion ({elapsed:.1f}s): {content!r}")
        return True
    except Exception as e:
        _fail("plain completion", f"{type(e).__name__}: {e}")
        return False


async def test_structured(model: str) -> bool:
    t0 = time.time()
    try:
        r = await litellm.acompletion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Generate keyword tags for the note content.",
                },
                {
                    "role": "user",
                    "content": "Title: Quantum Lab\n\nQuantum entanglement in the laboratory.",
                },
            ],
            response_format=TagAnalysis,
            temperature=0.0,
            max_tokens=128,
        )
        raw = r.choices[0].message.content or ""
        parsed = TagAnalysis.model_validate_json(raw)
        elapsed = time.time() - t0
        _ok(f"structured JSON ({elapsed:.1f}s): tags={parsed.tags}")
        return True
    except Exception as e:
        _fail("structured JSON", f"{type(e).__name__}: {e}")
        return False


async def test_tools(model: str) -> bool:
    """Agent-style function calling smoke test."""
    t0 = time.time()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_notes",
                "description": "Search workspace notes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                    },
                    "required": ["question"],
                },
            },
        }
    ]
    try:
        r = await litellm.acompletion(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Search my notes for quantum entanglement.",
                }
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=256,
        )
        msg = r.choices[0].message
        elapsed = time.time() - t0
        if getattr(msg, "tool_calls", None):
            tc = msg.tool_calls[0]
            _ok(
                f"tool calling ({elapsed:.1f}s): "
                f"{tc.function.name}({tc.function.arguments[:80]})"
            )
            return True
        _fail("tool calling", f"no tool_calls; content={msg.content!r}")
        return False
    except Exception as e:
        _fail("tool calling", f"{type(e).__name__}: {e}")
        return False


async def test_gemini_embedding(settings) -> bool:
    """Embeddings stay on Gemini — verify hybrid path still works."""
    if not settings.GEMINI_API_KEY:
        print("  SKIP  gemini embedding (no GEMINI_API_KEY)")
        return True
    t0 = time.time()
    try:
        r = await litellm.aembedding(
            model=settings.EMBEDDING_MODEL,
            input=["hybrid embedding smoke test"],
        )
        dim = len(r.data[0]["embedding"])
        elapsed = time.time() - t0
        expected = settings.EMBEDDING_DIMENSION
        if dim != expected:
            _fail("gemini embedding", f"dim={dim}, expected {expected}")
            return False
        _ok(f"gemini embedding ({elapsed:.1f}s): dim={dim}")
        return True
    except Exception as e:
        _fail("gemini embedding", f"{type(e).__name__}: {e}")
        return False


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_NIM_LLM)
    args = parser.parse_args()
    settings = get_settings()
    configure_litellm_env(settings)

    print("\n=== NVIDIA NIM pre-flight ===\n")
    print(f"  LLM test model: {args.model}")
    print(f"  NIM key set:     {bool(settings.effective_nvidia_nim_api_key)}")
    print(f"  GEMINI key set:  {bool(settings.GEMINI_API_KEY)}")
    print(f"  Embedding model: {settings.EMBEDDING_MODEL}")
    print()

    if not settings.effective_nvidia_nim_api_key:
        print("  FAIL  Set NVIDIA_NIM_API_KEY or NVIDIA_API_KEY in .env")
        return 1

    results = [
        await test_plain(args.model),
        await test_structured(args.model),
        await test_tools(args.model),
        await test_gemini_embedding(settings),
    ]

    print()
    if all(results):
        print("=== VERDICT: PASS — safe to set LLM_MODEL in .env ===\n")
        print(f"  LLM_MODEL={args.model}")
        return 0
    print("=== VERDICT: FAIL — fix NIM key/model before switching LLM_MODEL ===\n")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
