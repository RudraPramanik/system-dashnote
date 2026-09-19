"""
Helpers for the L2 DeepEval quality CLI. No deepeval import (CI-safe).

Judge credential is GEMINI_API_KEY_2 only — never GEMINI_API_KEY.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

# Reuse shared judge/chat helpers from the RAGAS lab (same credential law).
from ragas_lab import (  # noqa: F401 — re-exported for tests / CLI
    JUDGE_ENV,
    PRODUCT_GEMINI_ENV,
    JudgeKeyError,
    chat_payload,
    load_dotenv_repo,
    load_judge_key,
    search_context_texts,
    search_params,
)

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
GOLDEN_RAG_ANSWERS = EVALS_ROOT / "golden" / "rag_answers.jsonl"
REQUIREMENTS_QUALITY = EVALS_ROOT / "requirements-quality.txt"

DEFAULT_JUDGE_MODEL = "gemini-3.6-flash"
DEFAULT_BASE_URL = "http://127.0.0.1"
DEFAULT_HARD_FLOOR = 0.7
REQUIRED_METRICS = ("correctness", "completeness")
ALL_METRICS = ("correctness", "completeness", "style")

STYLE_RUBRIC = (
    "Citations should come from retrieved notes when available; "
    "be concise; do not invent certainty; "
    "do not claim private notes the user cannot see."
)

COLLECTION_FAILURE_HINT = (
    "ERROR: L2 quality collection failed — zero scored rows.\n"
    "This is a collection / API failure, not a DeepEval pin failure.\n"
    "Preflight before re-running:\n"
    "  1) GET /health and GET /health/ai are ok\n"
    "  2) JWT is valid; seed answer notes (--seed-live) or reuse L1 marker seeds\n"
    "  3) POST /ai/chat returns 200 with a non-empty answer and retrieval context\n"
    "  4) If chat is HTTP 500, check API logs (often LLM 429 quota) — "
    "switch to a different NVIDIA NIM free/catalog model via "
    "LLM_MODEL / LLM_MODEL_FALLBACKS, recreate api + worker, re-run\n"
    "  5) Empty answer / empty retrieval SKIPs the row — seed before scoring"
)


def load_rag_answer_goldens(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or GOLDEN_RAG_ANSWERS
    cases: list[dict[str, Any]] = []
    with target.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                cases.append(obj)
    return cases


def select_rag_answer_cases(
    cases: list[dict[str, Any]], *, limit: int | None
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for case in cases:
        theme = str(case.get("theme") or "")
        if theme and theme != "rag_answer":
            continue
        selected.append(case)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def classify_collection_skip(
    *,
    status_code: int | None,
    answer: str,
    retrieval_texts: list[str],
    chunks_retrieved: int | None = None,
) -> str | None:
    """
    Return a SKIP reason, or None if the row is eligible for judging.

    Empty answer or empty retrieval context MUST skip (not score as success).
    """
    if status_code is not None and status_code != 200:
        return f"chat HTTP {status_code}"
    if not (answer or "").strip():
        return "empty answer"
    if chunks_retrieved is not None and chunks_retrieved <= 0:
        return "empty retrieval"
    if not retrieval_texts:
        return "empty retrieval"
    return None


def checklist_text(case: dict[str, Any]) -> str:
    items = case.get("completeness_checklist") or []
    lines = [str(x).strip() for x in items if str(x).strip()]
    return "; ".join(lines)


def mean_finite(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if not nums:
        return None
    return sum(nums) / len(nums)


def aggregate_metric_scores(
    per_case: list[dict[str, Any]],
) -> dict[str, float | None]:
    """Map metric name -> mean of finite scores (None if all missing/NaN)."""
    out: dict[str, float | None] = {}
    for name in ALL_METRICS:
        vals: list[float | None] = []
        for row in per_case:
            scores = row.get("scores") or {}
            raw = scores.get(name)
            if raw is None:
                vals.append(None)
                continue
            try:
                fval = float(raw)
            except (TypeError, ValueError):
                vals.append(None)
                continue
            vals.append(None if math.isnan(fval) else fval)
        out[name] = mean_finite(vals)
    return out


def hard_floors_met(
    aggregates: Mapping[str, float | None],
    *,
    floor: float = DEFAULT_HARD_FLOOR,
) -> tuple[bool, list[str]]:
    """Correctness + completeness must be numeric and >= floor. Style is not gated."""
    problems: list[str] = []
    for name in REQUIRED_METRICS:
        val = aggregates.get(name)
        if val is None:
            problems.append(f"{name}=NaN/missing")
            continue
        if float(val) < float(floor):
            problems.append(f"{name}={val:.4f} < floor {floor}")
    return (not problems), problems


def configure_judge_env(judge_key: str, environ: dict[str, str] | None = None) -> None:
    """
    Point DeepEval Gemini at the dedicated judge key via GOOGLE_API_KEY.

    MUST NOT assign PRODUCT_GEMINI_ENV (embeddings / chat fallback).
    """
    env = os.environ if environ is None else environ
    env["GOOGLE_API_KEY"] = judge_key
    env["USE_GEMINI_MODEL"] = "1"
