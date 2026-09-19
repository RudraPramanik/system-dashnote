"""
Helpers for the operator RAGAS lab. No ragas import (CI-safe).

Judge credential is GEMINI_API_KEY_2 only — never GEMINI_API_KEY.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

JUDGE_ENV = "GEMINI_API_KEY_2"
PRODUCT_GEMINI_ENV = "GEMINI_API_KEY"
SKIP_CASE_IDS = frozenset({"ret-08-irrelevant-emptyish"})
DEFAULT_JUDGE_MODEL = "gemini-3.6-flash"
DEFAULT_BASE_URL = "http://127.0.0.1"
DEFAULT_LIMIT = 5

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
GOLDEN_RETRIEVAL = EVALS_ROOT / "golden" / "retrieval.jsonl"


class JudgeKeyError(Exception):
    """Dedicated judge key missing; do not fall back to product Gemini."""


class JudgeStackError(Exception):
    """Installed ragas/extra cannot build a Gemini judge; reinstall operator pin."""


REQUIREMENTS_RAGAS = EVALS_ROOT / "requirements-ragas.txt"

JUDGE_STACK_HINT = (
    "Installed ragas does not support Gemini "
    'llm_factory(..., provider="google", client=...). '
    "Reinstall the operator extra:\n"
    "  pip install -r evals/requirements-ragas.txt"
)

COLLECTION_FAILURE_HINT = (
    "ERROR: RAGAS collection failed — zero scored rows.\n"
    "This is a collection / API failure, not a RAGAS pin or judge-stack failure.\n"
    "Preflight before re-running --live:\n"
    "  1) GET /health and GET /health/ai are ok\n"
    "  2) JWT is valid; workspace has seeded retrieval notes (or run live seed)\n"
    "  3) POST /ai/chat returns 200 with chunks_retrieved > 0 for a golden query\n"
    "  4) If chat is HTTP 500, check API logs (often LLM 429 quota or stuck fallback cache)\n"
    "  5) Empty retrieval skips the row — seed markers before scoring"
)


def requirements_ragas_allows_google_factory(text: str | None = None) -> bool:
    """
    True when the operator pin can resolve a Gemini-capable ragas.

    Rejects the broken combo that forced OpenAI-only 0.3.2
    (`ragas<0.4` and/or `datasets<4`).
    """
    raw = text if text is not None else REQUIREMENTS_RAGAS.read_text(encoding="utf-8")
    code_lines = [
        line.split("#", 1)[0].strip().lower()
        for line in raw.splitlines()
        if line.split("#", 1)[0].strip()
    ]
    ragas_specs = [ln for ln in code_lines if ln.startswith("ragas")]
    if not ragas_specs:
        return False
    ragas_blob = "".join(spec.replace(" ", "") for spec in ragas_specs)
    if "<0.4" in ragas_blob:
        return False
    if ">=0.4" not in ragas_blob and not any(
        part.startswith("==0.4") for part in ragas_blob.split(",")
    ):
        return False
    for spec in code_lines:
        if spec.startswith("datasets") and "<4" in spec.replace(" ", ""):
            return False
    return True


def evaluation_dataset_dict(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Map collected lab rows to RAGAS 0.4+ single-turn column names."""
    return {
        "user_input": [r["question"] for r in rows],
        "response": [r["answer"] for r in rows],
        "retrieved_contexts": [r["contexts"] for r in rows],
        "reference": [r["reference"] for r in rows],
    }


def numeric_metric_aggregates(result: Any) -> list[float]:
    """
    Pull faithfulness / context_precision means from a RAGAS EvaluationResult.

    Uses `_repr_dict` (what `print(result)` shows). Returns only finite floats.
    """
    import math

    scores = getattr(result, "_repr_dict", None)
    if not isinstance(scores, dict):
        return []
    out: list[float] = []
    for key in ("faithfulness", "context_precision"):
        val = scores.get(key)
        try:
            fval = float(val)
        except (TypeError, ValueError):
            continue
        if not math.isnan(fval):
            out.append(fval)
    return out


def load_dotenv_repo() -> None:
    """Load repo `.env` if python-dotenv is available. Does not overwrite set vars."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def load_judge_key(environ: Mapping[str, str] | None = None) -> str:
    """
    Return stripped GEMINI_API_KEY_2.

    MUST NOT read or copy PRODUCT_GEMINI_ENV (embeddings / chat fallback).
    """
    env = os.environ if environ is None else environ
    raw = env.get(JUDGE_ENV, "")
    key = str(raw or "").strip()
    if not key:
        raise JudgeKeyError(
            f"{JUDGE_ENV} is required for the RAGAS lab; "
            f"will not fall back to {PRODUCT_GEMINI_ENV}."
        )
    return key


def chat_payload(message: str) -> dict[str, str]:
    """POST /ai/chat body — message only; never workspace_id."""
    return {"message": message}


def search_params(query: str, *, limit: int = 5) -> dict[str, Any]:
    """GET /ai/test-search query — q + limit only; never workspace_id."""
    return {"q": query, "limit": limit}


def citation_context_texts(payload: dict[str, Any]) -> list[str]:
    """Best-effort texts from chat citations (schema has no chunk body today)."""
    texts: list[str] = []
    for item in payload.get("citations") or []:
        if not isinstance(item, dict):
            continue
        for key in ("text", "chunk_text", "content"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())
                break
        else:
            title = item.get("title")
            if isinstance(title, str) and title.strip():
                texts.append(title.strip())
    return texts


def search_context_texts(payload: Any) -> list[str]:
    """Chunk texts from GET /ai/test-search (list or {results: [...]})."""
    hits: list[Any]
    if isinstance(payload, list):
        hits = payload
    elif isinstance(payload, dict):
        hits = payload.get("results") or payload.get("raw") or []
    else:
        hits = []
    texts: list[str] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        chunk = hit.get("content_chunk") or {}
        text = (
            hit.get("chunk_text")
            or (chunk.get("text") if isinstance(chunk, dict) else None)
            or hit.get("text")
            or ""
        )
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    return texts


def select_retrieval_cases(cases: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for case in cases:
        cid = str(case.get("id") or "")
        if case.get("theme") != "retrieval":
            continue
        if cid in SKIP_CASE_IDS:
            continue
        if case.get("expect_max_hits") == 0:
            continue
        if not case.get("query_text"):
            continue
        selected.append(case)
        if len(selected) >= limit:
            break
    return selected


def load_retrieval_goldens(path: Path | None = None) -> list[dict[str, Any]]:
    import json

    target = path or GOLDEN_RETRIEVAL
    cases: list[dict[str, Any]] = []
    if not target.exists():
        return cases
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(json.loads(line))
    return cases
