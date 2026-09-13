#!/usr/bin/env python3
"""
Fixed local query set for cost/latency sampling (interview D4).

Usage (Compose up, JWT ready):

  $env:PYTHONPATH = "src"
  $env:SAMPLE_BASE_URL = "http://127.0.0.1"
  $env:SAMPLE_TOKEN = "<access_token>"
  python scripts/sample_cost_latency.py

Without a live API, prints the offline local/sample methodology used when
Compose is down (empty-retrieval skip + budget caps). Never invents
production SLOs.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

# Fixed N=5 queries — keep stable so before/after runs compare apples-to-apples.
QUERY_SET = [
    "Summarize what is in my notes.",
    "What milestones are mentioned?",
    "completely unrelated zxqv nonsense phrase",  # likely empty retrieval
    "List any security review findings.",
    "What files have I uploaded?",
]


def _post_chat(base_url: str, token: str, message: str) -> dict:
    url = base_url.rstrip("/") + "/ai/chat"
    body = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode("utf-8")
    latency_ms = int((time.perf_counter() - t0) * 1000)
    data = json.loads(raw)
    data["_client_latency_ms"] = latency_ms
    return data


def offline_methodology() -> None:
    print("MODE: offline local/sample (no SAMPLE_TOKEN / unreachable API)")
    print("Label: local/sample — NOT a production SLO")
    print()
    print("Fixed query set (N=%d):" % len(QUERY_SET))
    for i, q in enumerate(QUERY_SET, 1):
        print(f"  {i}. {q}")
    print()
    print("Architecture cost controls (measured by code path, not live $):")
    print("  - TOKEN_BUDGET_PER_REQUEST = 8000 chars context budget")
    print("  - LLM_MAX_TOKENS = 2048 completion cap (chat/agent)")
    print("  - LLM_STRUCTURED_MAX_TOKENS_TAGS = 256")
    print("  - LLM_STRUCTURED_MAX_TOKENS_METADATA = 512")
    print("  - Empty retrieval: generation tokens = 0 (skip LLM)")
    print("  - Embed cache hit: provider embed calls = 0 for identical text")
    print()
    print("Optimization comparison (EXP-002):")
    print("  BEFORE: empty query still billed a full chat completion (up to 2048 tokens)")
    print("  AFTER:  empty query generation cost = 0 tokens / $0 generation")
    print("  BEFORE: re-embed identical chunk text -> provider call each time")
    print("  AFTER:  cache hit -> 0 provider embed calls")
    print()
    print("Re-run with SAMPLE_BASE_URL + SAMPLE_TOKEN for latency_ms + Langfuse $.")


def main() -> int:
    base = os.environ.get("SAMPLE_BASE_URL", "http://127.0.0.1").rstrip("/")
    token = os.environ.get("SAMPLE_TOKEN", "").strip()
    if not token:
        offline_methodology()
        return 0

    rows = []
    print("MODE: live local sample")
    print("Label: local/sample — NOT a production SLO")
    print(f"base_url={base}")
    for q in QUERY_SET:
        try:
            data = _post_chat(base, token, q)
        except urllib.error.URLError as e:
            print(f"ERROR calling API: {e}", file=sys.stderr)
            print("Falling back to offline methodology.", file=sys.stderr)
            offline_methodology()
            return 1
        rows.append(
            {
                "query": q,
                "latency_ms": data.get("latency_ms", data.get("_client_latency_ms")),
                "chunks_retrieved": data.get("chunks_retrieved"),
                "chunks_used": data.get("chunks_used"),
                "answer_prefix": (data.get("answer") or "")[:80],
            }
        )
        print(json.dumps(rows[-1], ensure_ascii=False))

    latencies = [r["latency_ms"] for r in rows if isinstance(r["latency_ms"], int)]
    if latencies:
        print(
            "summary:",
            json.dumps(
                {
                    "n": len(latencies),
                    "latency_ms_avg": round(sum(latencies) / len(latencies)),
                    "latency_ms_max": max(latencies),
                    "emptyish": sum(
                        1 for r in rows if (r.get("chunks_retrieved") or 0) == 0
                    ),
                }
            ),
        )
    print("Export token/$ from Langfuse rag.answer → llm_generation when configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
