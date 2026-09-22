"""
Helpers for the L2 DeepEval quality CLI. No deepeval import (CI-safe).

Default judge is NVIDIA NIM (a different catalog id than product Lightning).
Gemini (`GEMINI_API_KEY_2`) remains an opt-in `--judge-backend gemini`. Never GEMINI_API_KEY.
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

DEFAULT_JUDGE_MODEL = "nvidia_nim/openai/gpt-oss-20b"
DEFAULT_JUDGE_BACKEND = "nim"
DEFAULT_BASE_URL = "http://127.0.0.1"
DEFAULT_HARD_FLOOR = 0.7
DEFAULT_COLLECTION_TIMEOUT = 300.0
CHAT_TIMEOUT_RETRY_SLEEP_SEC = 5.0
REQUIRED_METRICS = ("correctness", "completeness")
ALL_METRICS = ("correctness", "completeness", "style")

STYLE_RUBRIC = (
    "Be concise. Do not invent facts. "
    "When the answer uses a marker token from the retrieved notes, preserve that token exactly. "
    "When context is insufficient, the only allowed non-answer is: "
    '"I could not find relevant information in your notes and files for this query." '
    "Score the answer text only. Do not require citation prose inside the answer."
)

# DeepEval GEval asks for an integer on its default 0–10 range and divides by 10.
# These steps must not tell the judge to score from 0 to 1.
CORRECTNESS_STEPS = [
    "Compare actual output facts to the expected output.",
    "Penalize contradictions and invented facts.",
    "Do not penalize harmless wording differences.",
]
COMPLETENESS_STEPS = [
    "Treat expected output as the completeness checklist.",
    "Check whether every required checklist point appears in the actual output.",
    "Missing a required point should lower the score.",
]
STYLE_STEPS = [
    f"Score against this product voice rubric: {STYLE_RUBRIC}",
    "Low style is an honest outcome.",
]

QUALITY_SCORES_PATH = EVALS_ROOT / "quality_scores.jsonl"
EVAL_REPORT_2_PATH = EVALS_ROOT / "eval_report_2.md"

COLLECTION_FAILURE_HINT = (
    "ERROR: L2 quality collection failed — zero scored rows.\n"
    "This is a collection / API failure, not a DeepEval pin failure.\n"
    "Preflight before re-running:\n"
    "  1) GET /health and GET /health/ai are ok\n"
    "  2) JWT is valid; seed answer notes (--seed-live) or reuse L1 marker seeds\n"
    "  3) POST /ai/chat returns 200 with a non-empty answer and retrieval context\n"
    "  4) Chat HTTP timeout / transport SKIP is expected on a slow NIM turn — "
    "raise --timeout (default 300s) or use --limit for smoke; remaining cases "
    "still run. Uncaught timeout traceback is a harness bug.\n"
    "  5) If chat is HTTP 500, check API logs (often LLM 429 quota) — "
    "switch to a different NVIDIA NIM free/catalog model via "
    "LLM_MODEL / LLM_MODEL_FALLBACKS, recreate api + worker, re-run\n"
    "  6) Empty answer / empty retrieval / timeout SKIPs the row — seed before scoring"
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


def transport_skip_reason(exc: BaseException, *, surface: str) -> str:
    """
    Map HTTP client timeout / other request-transport failures to a SKIP reason.

    surface is ``chat`` (POST /ai/chat) or ``search`` (GET /ai/test-search).
    """
    label = "chat" if surface == "chat" else "search"
    cls = type(exc).__name__.lower()
    text = str(exc).lower()
    if "timeout" in cls or "timeout" in text:
        return f"{label} timeout"
    return f"{label} transport error"


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


def reset_quality_scores(path: Path | None = None) -> Path:
    """Replace the scores JSONL so a new run cannot mix with the previous one."""
    target = path or QUALITY_SCORES_PATH
    target.write_text("", encoding="utf-8")
    return target


def append_quality_score(row: dict[str, Any], path: Path | None = None) -> None:
    """Append one scored case. Reasons are stored even when scores are numeric."""
    target = path or QUALITY_SCORES_PATH
    record = {
        "id": row.get("id"),
        "scores": row.get("scores") or {},
        "reasons": row.get("reasons") or {},
    }
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_quality_scores(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or QUALITY_SCORES_PATH
    rows: list[dict[str, Any]] = []
    if not target.exists():
        return rows
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def render_eval_report_2(
    rows: list[dict[str, Any]],
    *,
    environment: str,
    judge_model: str,
    skip_reasons: list[str],
    floor: float,
    aggregates: dict[str, float | None] | None = None,
) -> str:
    """Markdown report rendered from scored JSONL rows. Full reasons stay in the file."""
    means = aggregates if aggregates is not None else aggregate_metric_scores(rows)
    lines = [
        "# L2 quality report",
        "",
        "Rendered from `evals/quality_scores.jsonl`. The console transcript is not the record.",
        "",
        f"- environment: `{environment}`",
        f"- judge_model: `{judge_model}`",
        f"- n: {len(rows)}",
        f"- SKIP: {len(skip_reasons)}",
        f"- floor: {floor} (correctness and completeness; style is not gated)",
        "",
        "## Aggregates",
        "",
    ]
    for name in ALL_METRICS:
        val = means.get(name)
        shown = "NaN" if val is None else f"{float(val):.4f}"
        lines.append(f"- {name}: {shown}")
    if skip_reasons:
        lines.extend(["", "## SKIP reasons", ""])
        for reason in skip_reasons:
            lines.append(f"- {reason}")
    lines.extend(["", "## Cases", ""])
    for row in rows:
        scores = row.get("scores") or {}
        reasons = row.get("reasons") or {}
        lines.append(f"### {row.get('id')}")
        lines.append("")
        for name in ALL_METRICS:
            raw = scores.get(name)
            shown = "NaN" if raw is None else f"{float(raw):.4f}"
            lines.append(f"- {name}: {shown}")
            reason = str(reasons.get(name) or "").strip()
            if reason:
                lines.append(f"  - reason: {reason}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def configure_judge_env(judge_key: str, environ: dict[str, str] | None = None) -> None:
    """
    Point DeepEval Gemini at the dedicated judge key via GOOGLE_API_KEY.

    MUST NOT assign PRODUCT_GEMINI_ENV (embeddings / chat fallback).
    """
    env = os.environ if environ is None else environ
    env["GOOGLE_API_KEY"] = judge_key
    env["USE_GEMINI_MODEL"] = "1"
