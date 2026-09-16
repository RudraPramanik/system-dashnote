#!/usr/bin/env python3
"""
Operator/nightly RAGAS lab (faithfulness + context precision).

NOT invoked from PR CI. NOT deployed on the VPS. Chat/agent never await this.

From repo root:

    pip install -r evals/requirements-ragas.txt
    python evals/run_ragas.py --setup
    python evals/run_ragas.py --live --token "<jwt>"

Requires GEMINI_API_KEY_2 (dedicated judge). Never uses GEMINI_API_KEY.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

from ragas_lab import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_LIMIT,
    JUDGE_ENV,
    JUDGE_STACK_HINT,
    PRODUCT_GEMINI_ENV,
    JudgeKeyError,
    JudgeStackError,
    chat_payload,
    evaluation_dataset_dict,
    load_dotenv_repo,
    load_judge_key,
    load_retrieval_goldens,
    numeric_metric_aggregates,
    search_context_texts,
    search_params,
    select_retrieval_cases,
)

SETUP_TEXT = f"""
DashNote RAGAS lab — local / nightly only (not VPS, not PR CI)
==============================================================
1. On the laptop (not the API image):
     pip install -r evals/requirements-ragas.txt
2. Set {JUDGE_ENV} in local .env (dedicated Google AI Studio project).
   Do NOT reuse {PRODUCT_GEMINI_ENV} (embeddings / chat fallback).
   Do NOT copy {JUDGE_ENV} to Compose, VPS, or src/config.py.
3. Bring local Compose up. Get a JWT (register/login).
4. Run:
     python evals/run_ragas.py --live --token "<jwt>"
   Defaults: --base-url {DEFAULT_BASE_URL} --limit {DEFAULT_LIMIT}
   --judge-model {DEFAULT_JUDGE_MODEL}
5. Record faithfulness + context_precision in docs/EXPERIMENTS.md
   with environment=lab (or live-local). Not a production SLO.
6. Do NOT add this script to .github/workflows/ci.yml.
7. Do NOT point --base-url at production HTTPS as a merge gate.
""".strip()


def _print_setup() -> int:
    print(SETUP_TEXT)
    return 0


def _collect_row(
    client: Any,
    headers: dict[str, str],
    case: dict[str, Any],
) -> dict[str, Any] | None:
    query = str(case["query_text"])
    cid = str(case.get("id") or "")
    chat_res = client.post("/ai/chat", headers=headers, json=chat_payload(query))
    if chat_res.status_code != 200:
        print(f"  SKIP  {cid}: chat {chat_res.status_code} {chat_res.text[:160]}")
        return None
    chat_body = chat_res.json()
    if not isinstance(chat_body, dict):
        print(f"  SKIP  {cid}: chat payload not an object")
        return None
    answer = str(chat_body.get("answer") or "").strip()
    chunks_retrieved = int(chat_body.get("chunks_retrieved") or 0)

    search_res = client.get(
        "/ai/test-search",
        headers=headers,
        params=search_params(query, limit=5),
    )
    contexts: list[str] = []
    if search_res.status_code == 200:
        contexts = search_context_texts(search_res.json())

    if chunks_retrieved == 0 or not contexts:
        print(f"  SKIP  {cid}: empty retrieval / no context texts")
        return None
    if not answer:
        print(f"  SKIP  {cid}: empty answer")
        return None

    markers = [str(m) for m in (case.get("expect_content_markers") or []) if m]
    reference = " ".join(markers) if markers else answer
    print(f"  COLLECT {cid}: contexts={len(contexts)}")
    return {
        "id": cid,
        "question": query,
        "answer": answer,
        "contexts": contexts,
        "reference": reference,
    }


def _build_gemini_judge_llm(judge_key: str, judge_model: str) -> Any:
    """
    Build a Gemini RAGAS judge from GEMINI_API_KEY_2 only.

    Never assigns PRODUCT_GEMINI_ENV (embeddings / chat fallback).
    """
    from google import genai
    from ragas.llms import llm_factory

    os.environ["GOOGLE_API_KEY"] = judge_key
    client = genai.Client(api_key=judge_key)
    try:
        return llm_factory(judge_model, provider="google", client=client)
    except TypeError as exc:
        raise JudgeStackError(JUDGE_STACK_HINT) from exc


def _run_metrics(rows: list[dict[str, Any]], judge_key: str, judge_model: str) -> int:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import ContextPrecision, Faithfulness
    except ImportError as exc:
        print(
            "RAGAS extra missing. On the laptop run:\n"
            "  pip install -r evals/requirements-ragas.txt\n"
            f"({exc})",
            file=sys.stderr,
        )
        return 2

    try:
        llm = _build_gemini_judge_llm(judge_key, judge_model)
    except JudgeStackError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    dataset = Dataset.from_dict(evaluation_dataset_dict(rows))
    print(f"=== RAGAS evaluate n={len(rows)} judge={judge_model} ===\n")
    result = evaluate(
        dataset,
        metrics=[Faithfulness(llm=llm), ContextPrecision(llm=llm)],
    )
    print(result)
    if not numeric_metric_aggregates(result):
        print(
            "ERROR: RAGAS returned no numeric scores.\n"
            "  Check judge model availability (--judge-model) and reinstall:\n"
            "  pip install -r evals/requirements-ragas.txt\n"
            "  (Gemini structured output needs instructor[google-genai] / jsonref.)",
            file=sys.stderr,
        )
        return 2
    print("\nLabel environment=lab in docs/EXPERIMENTS.md. Not a production SLO.")
    return 0


def _run_live(args: argparse.Namespace) -> int:
    load_dotenv_repo()
    try:
        judge_key = load_judge_key()
    except JudgeKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not args.token:
        print("ERROR: --token required for --live", file=sys.stderr)
        return 1

    import httpx

    cases = select_retrieval_cases(load_retrieval_goldens(), limit=int(args.limit))
    if not cases:
        print("No retrieval goldens selected.", file=sys.stderr)
        return 1

    print(
        f"=== RAGAS live base={args.base_url} cases={len(cases)} "
        f"(skipped tenant/trajectory/empty) ===\n"
    )
    rows: list[dict[str, Any]] = []
    headers = {"Authorization": f"Bearer {args.token}"}
    with httpx.Client(base_url=str(args.base_url).rstrip("/"), timeout=120.0) as client:
        for case in cases:
            row = _collect_row(client, headers, case)
            if row:
                rows.append(row)

    if not rows:
        print("No rows collected (empty retrieval or chat errors).", file=sys.stderr)
        return 1
    return _run_metrics(rows, judge_key, str(args.judge_model))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Operator RAGAS lab (not CI, not VPS)."
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Print install/env/run checklist; no network or judge calls.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Collect local chat+search triples and score with RAGAS.",
    )
    parser.add_argument("--base-url", default=os.environ.get("EVAL_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token", default=os.environ.get("EVAL_TOKEN") or None)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    args = parser.parse_args()

    if args.live and args.setup:
        print("ERROR: use --setup or --live, not both", file=sys.stderr)
        return 1
    if args.live:
        return _run_live(args)
    return _print_setup()


if __name__ == "__main__":
    raise SystemExit(main())
