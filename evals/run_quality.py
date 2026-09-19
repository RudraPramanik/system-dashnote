#!/usr/bin/env python3
"""
L2 LLM-as-judge quality CLI (DeepEval GEval).

NOT invoked from PR CI. NOT deployed on the VPS. Chat/agent never await this.

From repo root:

    pip install -r evals/requirements-quality.txt
    $env:PYTHONPATH = "src"
    python evals/run_quality.py --token "<jwt>" --base-url http://127.0.0.1

Requires GEMINI_API_KEY_2 (dedicated judge). Never uses GEMINI_API_KEY.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

from quality_lab import (  # noqa: E402
    ALL_METRICS,
    COLLECTION_FAILURE_HINT,
    DEFAULT_BASE_URL,
    DEFAULT_HARD_FLOOR,
    DEFAULT_JUDGE_MODEL,
    REQUIRED_METRICS,
    STYLE_RUBRIC,
    JudgeKeyError,
    PRODUCT_GEMINI_ENV,
    JUDGE_ENV,
    aggregate_metric_scores,
    chat_payload,
    checklist_text,
    classify_collection_skip,
    configure_judge_env,
    hard_floors_met,
    load_dotenv_repo,
    load_judge_key,
    load_rag_answer_goldens,
    search_context_texts,
    search_params,
    select_rag_answer_cases,
)

SETUP_TEXT = f"""
DashNote L2 quality CLI — local / pre-deploy only (not VPS, not PR CI)
=====================================================================
1. On the laptop (not the API image):
     pip install -r evals/requirements-quality.txt
2. Set {JUDGE_ENV} in local .env (dedicated Google AI Studio project).
   Do NOT reuse {PRODUCT_GEMINI_ENV} (embeddings / chat fallback).
   Do NOT copy {JUDGE_ENV} to Compose, VPS, or src/config.py.
3. Bring local Compose up. Confirm GET /health and GET /health/ai.
4. Prefer a stack already proven by L1 live. Get a JWT; seed answer notes
   with --seed-live (reuses retrieval-marker seed content) or seed offline.
5. If product chat/embed hits Gemini 429, switch to a different NVIDIA NIM
   free/catalog model via LLM_MODEL / LLM_MODEL_FALLBACKS, recreate api +
   worker, then re-run. Do not put a judge on /ai/chat or /ai/agent.
6. Run:
     python evals/run_quality.py --token "<jwt>" --base-url http://127.0.0.1
   Optional: --limit N --judge-model {DEFAULT_JUDGE_MODEL} --seed-live
   --environment lab|pre-deploy --floor {DEFAULT_HARD_FLOOR}
7. Record correctness / completeness / style (+ n / SKIPs / judge model) in
   evals/README.md with environment=lab or pre-deploy. Not a production SLO.
8. Do NOT add this script to .github/workflows/ci.yml.
""".strip()


def _print_setup() -> int:
    print(SETUP_TEXT)
    return 0


def _seed_notes(client: Any, headers: dict[str, str], cases: list[dict[str, Any]]) -> None:
    max_wait = 0
    seen: set[str] = set()
    for case in cases:
        seed = case.get("seed")
        if not isinstance(seed, dict):
            continue
        key = f"{seed.get('title')}|{seed.get('content')}"
        if key in seen:
            continue
        seen.add(key)
        nb = client.post(
            "/notebooks/",
            headers=headers,
            json={"name": f"L2 Eval NB {uuid.uuid4().hex[:6]}"},
        )
        nb.raise_for_status()
        note = client.post(
            "/notes/",
            headers=headers,
            json={
                "title": seed.get("title") or "L2 eval note",
                "content": seed.get("content") or "",
                "is_private": bool(seed.get("is_private", False)),
            },
        )
        note.raise_for_status()
        max_wait = max(max_wait, int(seed.get("wait_embed_sec") or 0))
    if seen and max_wait > 0:
        print(f"  ... seeded {len(seen)} notes; waiting {max_wait}s for embeds")
        time.sleep(max_wait)


def _collect_row(
    client: Any,
    headers: dict[str, str],
    case: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    query = str(case.get("query_text") or "")
    cid = str(case.get("id") or "")
    chat_res = client.post("/ai/chat", headers=headers, json=chat_payload(query))
    status = chat_res.status_code
    answer = ""
    chunks_retrieved: int | None = None
    retrieval_texts: list[str] = []

    if status == 200:
        chat_body = chat_res.json()
        if isinstance(chat_body, dict):
            answer = str(chat_body.get("answer") or "").strip()
            try:
                chunks_retrieved = int(chat_body.get("chunks_retrieved") or 0)
            except (TypeError, ValueError):
                chunks_retrieved = 0

    search_res = client.get(
        "/ai/test-search",
        headers=headers,
        params=search_params(query, limit=5),
    )
    if search_res.status_code == 200:
        retrieval_texts = search_context_texts(search_res.json())

    reason = classify_collection_skip(
        status_code=status,
        answer=answer,
        retrieval_texts=retrieval_texts,
        chunks_retrieved=chunks_retrieved,
    )
    if reason:
        return None, reason

    return (
        {
            "id": cid,
            "input": query,
            "actual_output": answer,
            "expected_output": str(case.get("expected_output") or ""),
            "completeness_checklist": checklist_text(case),
            "style_notes": str(case.get("style_notes") or STYLE_RUBRIC),
            "retrieval_context": retrieval_texts,
        },
        None,
    )


def _eval_params():
    """Resolve DeepEval param enum (name varies across versions)."""
    try:
        from deepeval.test_case import SingleTurnParams as params
    except ImportError:  # pragma: no cover
        from deepeval.test_case import LLMTestCaseParams as params  # type: ignore
    return params


def _resolve_judge_model(judge_model: str, judge_backend: str) -> Any:
    """
    Gemini (GEMINI_API_KEY_2 → GOOGLE_API_KEY) by default.

    When Gemini judge is 503/429, operators may pass --judge-backend nim with a
    different free/catalog NIM model. Uses a thin LiteLLM wrapper that asks for
    JSON in the prompt (NIM often rejects OpenAI response_format / logprobs).
    Never uses product GEMINI_API_KEY.
    """
    backend = (judge_backend or "gemini").lower()
    if backend == "nim" or judge_model.startswith("nvidia_nim/"):
        return _build_nim_judge_llm(judge_model)

    from deepeval.models import GeminiModel

    return GeminiModel(model=judge_model, api_key=os.environ.get("GOOGLE_API_KEY"))


def _build_nim_judge_llm(judge_model: str) -> Any:
    import json
    import re

    import litellm
    from deepeval.models import DeepEvalBaseLLM
    from pydantic import BaseModel

    litellm.drop_params = True
    nim_key = (
        os.environ.get("NVIDIA_NIM_API_KEY")
        or os.environ.get("NVIDIA_API_KEY")
        or ""
    ).strip()
    if not nim_key:
        raise RuntimeError(
            "NVIDIA_NIM_API_KEY (or NVIDIA_API_KEY) is required for "
            "--judge-backend nim / nvidia_nim/* judge models."
        )
    model_id = judge_model
    if not model_id.startswith("nvidia_nim/"):
        model_id = f"nvidia_nim/{model_id}"

    def _extract_json(text: str) -> dict[str, Any]:
        raw = (text or "").strip()
        if not raw:
            raise ValueError("empty judge response")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    class NimGEvalLLM(DeepEvalBaseLLM):
        def __init__(self, model: str, api_key: str) -> None:
            self._model = model
            self._api_key = api_key

        def load_model(self) -> str:
            return self._model

        def get_model_name(self) -> str:
            return self._model

        def generate(self, prompt: str, schema: type[BaseModel] | None = None):  # type: ignore[override]
            messages = [{"role": "user", "content": prompt}]
            if schema is not None:
                messages = [
                    {
                        "role": "user",
                        "content": (
                            f"{prompt}\n\n"
                            "Respond with a single JSON object that matches this schema "
                            f"(no markdown):\n{json.dumps(schema.model_json_schema())}"
                        ),
                    }
                ]
            last_exc: Exception | None = None
            for attempt in range(3):
                try:
                    response = litellm.completion(
                        model=self._model,
                        messages=messages,
                        api_key=self._api_key,
                        temperature=0.0,
                        max_tokens=512,
                        timeout=180,
                    )
                    content = response.choices[0].message.content or ""
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    msg = str(exc).lower()
                    retryable = any(
                        s in msg
                        for s in ("timeout", "429", "503", "unavailable", "rate")
                    )
                    if retryable and attempt < 2:
                        time.sleep(8 * (attempt + 1))
                        continue
                    raise
            if last_exc is not None:
                raise last_exc
            # Custom (non-native) DeepEval models must return schema/str only —
            # not (result, cost); sync generate_with_schema_and_extract does not unwrap.
            if schema is None:
                return content
            payload = _extract_json(content)
            return schema(**payload)

        async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None):  # type: ignore[override]
            return self.generate(prompt, schema=schema)

    return NimGEvalLLM(model_id, nim_key)


def _build_metrics(judge_model: str, floor: float, judge_backend: str) -> list[Any]:
    from deepeval.metrics import GEval

    params = _eval_params()
    model = _resolve_judge_model(judge_model, judge_backend)

    correctness = GEval(
        name="Correctness",
        evaluation_steps=[
            "Compare actual output facts to the expected output.",
            "Penalize contradictions and invented facts.",
            "Do not penalize harmless wording differences.",
            "Return a score from 0 to 1 with a short reason.",
        ],
        evaluation_params=[
            params.ACTUAL_OUTPUT,
            params.EXPECTED_OUTPUT,
        ],
        threshold=floor,
        model=model,
        async_mode=False,
    )
    completeness = GEval(
        name="Completeness",
        evaluation_steps=[
            "Treat expected output as the completeness checklist.",
            "Check whether every required checklist point appears in the actual output.",
            "Missing a required point should lower the score.",
            "Return a score from 0 to 1 with a short reason.",
        ],
        evaluation_params=[
            params.ACTUAL_OUTPUT,
            params.EXPECTED_OUTPUT,
        ],
        threshold=floor,
        model=model,
        async_mode=False,
    )
    style = GEval(
        name="Style",
        evaluation_steps=[
            f"Score against this product voice rubric: {STYLE_RUBRIC}",
            "Low style is an honest outcome; do not invent citations.",
            "Return a score from 0 to 1 with a short reason.",
        ],
        evaluation_params=[params.ACTUAL_OUTPUT],
        threshold=0.0,
        model=model,
        async_mode=False,
    )
    return [correctness, completeness, style]


def _score_rows(
    rows: list[dict[str, Any]],
    *,
    judge_model: str,
    floor: float,
    judge_backend: str,
) -> list[dict[str, Any]]:
    from deepeval.test_case import LLMTestCase

    metrics = _build_metrics(judge_model, floor, judge_backend)
    scored: list[dict[str, Any]] = []
    for row in rows:
        # Completeness uses checklist text as expected_output for that metric pass.
        tc_correct = LLMTestCase(
            input=row["input"],
            actual_output=row["actual_output"],
            expected_output=row["expected_output"],
            retrieval_context=row.get("retrieval_context") or [],
        )
        tc_complete = LLMTestCase(
            input=row["input"],
            actual_output=row["actual_output"],
            expected_output=row["completeness_checklist"] or row["expected_output"],
            retrieval_context=row.get("retrieval_context") or [],
        )
        tc_style = LLMTestCase(
            input=row["input"],
            actual_output=row["actual_output"],
            retrieval_context=row.get("retrieval_context") or [],
        )

        scores: dict[str, float | None] = {}
        reasons: dict[str, str] = {}
        for metric, tc, key in (
            (metrics[0], tc_correct, "correctness"),
            (metrics[1], tc_complete, "completeness"),
            (metrics[2], tc_style, "style"),
        ):
            last_exc: Exception | None = None
            for attempt in range(3):
                try:
                    metric.measure(tc)
                    raw = getattr(metric, "score", None)
                    try:
                        scores[key] = None if raw is None else float(raw)
                    except (TypeError, ValueError):
                        scores[key] = None
                    reasons[key] = str(getattr(metric, "reason", "") or "")
                    last_exc = None
                    break
                except Exception as exc:  # judge 429/503 / parse failures
                    last_exc = exc
                    msg = str(exc).lower()
                    retryable = any(
                        s in msg
                        for s in (
                            "429",
                            "503",
                            "unavailable",
                            "high demand",
                            "rate",
                            "timeout",
                        )
                    )
                    if retryable and attempt < 2:
                        # Quota / high-demand needs longer backoff than brief 503 blips.
                        delay = 45 if ("429" in msg or "quota" in msg or "resource_exhausted" in msg) else 12
                        time.sleep(delay * (attempt + 1))
                        continue
                    scores[key] = None
                    reasons[key] = f"judge error: {exc}"
                    break
            if last_exc is not None and key not in scores:
                scores[key] = None
                reasons[key] = f"judge error: {last_exc}"

        scored.append({"id": row["id"], "scores": scores, "reasons": reasons})
        c = scores.get("correctness")
        p = scores.get("completeness")
        s = scores.get("style")
        print(
            f"  SCORE  {row['id']}: "
            f"correctness={_fmt(c)} completeness={_fmt(p)} style={_fmt(s)}"
        )
        for key in ALL_METRICS:
            if scores.get(key) is None and reasons.get(key):
                print(f"         {key} reason: {reasons[key][:240]}")
    return scored


def _fmt(val: float | None) -> str:
    if val is None:
        return "NaN"
    return f"{val:.4f}"


def _run_live(args: argparse.Namespace) -> int:
    load_dotenv_repo()
    judge_backend = str(args.judge_backend or "gemini").lower()
    # Gemini path: dedicated GEMINI_API_KEY_2. NIM hatch: NVIDIA_NIM_API_KEY.
    # Never fall back to product GEMINI_API_KEY for judging.
    if judge_backend != "nim" and not str(args.judge_model).startswith("nvidia_nim/"):
        try:
            judge_key = load_judge_key()
        except JudgeKeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        configure_judge_env(judge_key)
        os.environ["GOOGLE_API_KEY"] = judge_key
    else:
        nim_key = (
            os.environ.get("NVIDIA_NIM_API_KEY")
            or os.environ.get("NVIDIA_API_KEY")
            or ""
        ).strip()
        if not nim_key:
            print(
                "ERROR: --judge-backend nim requires NVIDIA_NIM_API_KEY "
                f"(will not fall back to {PRODUCT_GEMINI_ENV}).",
                file=sys.stderr,
            )
            return 1
        judge_backend = "nim"

    if not args.token:
        print("ERROR: --token required (unless --setup)", file=sys.stderr)
        return 1

    try:
        import deepeval  # noqa: F401
    except ImportError as exc:
        print(
            "DeepEval extra missing. On the laptop run:\n"
            "  pip install -r evals/requirements-quality.txt\n"
            f"({exc})",
            file=sys.stderr,
        )
        return 2

    import httpx

    cases = select_rag_answer_cases(
        load_rag_answer_goldens(),
        limit=int(args.limit) if args.limit is not None else None,
    )
    if not cases:
        print("No rag_answer goldens selected.", file=sys.stderr)
        return 1

    environment = str(args.environment or "lab")
    floor = float(args.floor)
    judge_model = str(args.judge_model)

    print(
        f"=== L2 quality env={environment} base={args.base_url} "
        f"judge={judge_model} backend={judge_backend} "
        f"cases={len(cases)} floor={floor} ===\n"
    )

    headers = {"Authorization": f"Bearer {args.token}"}
    rows: list[dict[str, Any]] = []
    skip_reasons: list[str] = []

    with httpx.Client(base_url=str(args.base_url).rstrip("/"), timeout=180.0) as client:
        if args.seed_live:
            try:
                _seed_notes(client, headers, cases)
            except Exception as exc:
                print(f"ERROR: --seed-live failed: {exc}", file=sys.stderr)
                return 1
        for case in cases:
            cid = str(case.get("id") or "")
            row, reason = _collect_row(client, headers, case)
            if reason:
                skip_reasons.append(f"{cid}: {reason}")
                print(f"  SKIP  {cid}: {reason}")
                continue
            assert row is not None
            print(f"  COLLECT {cid}: contexts={len(row['retrieval_context'])}")
            rows.append(row)

    if not rows:
        print(COLLECTION_FAILURE_HINT, file=sys.stderr)
        print(f"SKIP count={len(skip_reasons)}", file=sys.stderr)
        for r in skip_reasons:
            print(f"  {r}", file=sys.stderr)
        return 1

    print(f"\n=== DeepEval GEval n={len(rows)} ===\n")
    scored = _score_rows(
        rows,
        judge_model=judge_model,
        floor=floor,
        judge_backend=judge_backend,
    )
    aggregates = aggregate_metric_scores(scored)

    print("\n=== Aggregates ===")
    print(f"environment={environment}")
    print(f"judge_model={judge_model}")
    print(f"n={len(scored)}")
    print(f"SKIP={len(skip_reasons)}")
    for r in skip_reasons:
        print(f"  SKIP reason: {r}")
    nan_notes: list[str] = []
    for name in ALL_METRICS:
        val = aggregates.get(name)
        print(f"{name}={_fmt(val)}")
        if val is None:
            nan_notes.append(name)
    if nan_notes:
        print(
            f"NaN notes: required/report metrics without numeric mean: {', '.join(nan_notes)}. "
            "Re-run with --judge-model or after judge quota resets; do not invent scores.",
            file=sys.stderr,
        )

    # Fail closed: any required metric all-NaN
    if any(aggregates.get(m) is None for m in REQUIRED_METRICS):
        print(
            "ERROR: required metrics correctness/completeness are NaN/non-numeric.",
            file=sys.stderr,
        )
        return 2

    ok, problems = hard_floors_met(aggregates, floor=floor)
    if not ok:
        print(
            "ERROR: hard floors not met: " + "; ".join(problems),
            file=sys.stderr,
        )
        return 1

    print(
        f"\nLabel environment={environment} in evals/README.md. Not a production SLO."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="L2 DeepEval quality CLI (not CI, not VPS)."
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Print install/env/run checklist; no network or judge calls.",
    )
    parser.add_argument("--base-url", default=os.environ.get("EVAL_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token", default=os.environ.get("EVAL_TOKEN") or None)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of rag_answer cases.",
    )
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument(
        "--judge-backend",
        default="gemini",
        choices=("gemini", "nim"),
        help=(
            "gemini = DeepEval GeminiModel via GEMINI_API_KEY_2; "
            "nim = LiteLLMModel via NVIDIA_NIM_API_KEY when Gemini judge is 503/429."
        ),
    )
    parser.add_argument(
        "--floor",
        type=float,
        default=DEFAULT_HARD_FLOOR,
        help="Hard floor for correctness and completeness aggregates.",
    )
    parser.add_argument(
        "--environment",
        default="lab",
        choices=("lab", "pre-deploy"),
        help="Honesty label printed with aggregates.",
    )
    parser.add_argument(
        "--seed-live",
        action="store_true",
        help="Create seed notes from goldens and wait for embeds before chat.",
    )
    args = parser.parse_args()

    if args.setup:
        return _print_setup()
    return _run_live(args)


if __name__ == "__main__":
    raise SystemExit(main())
