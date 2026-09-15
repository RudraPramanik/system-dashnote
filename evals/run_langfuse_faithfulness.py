#!/usr/bin/env python3
"""
Operator/nightly Langfuse dataset seed + faithfulness judge helper.

NOT invoked from PR CI. Chat and agent request paths do not call this.

From repo root:

    set PYTHONPATH=src
    python evals/run_langfuse_faithfulness.py --ui-only
    python evals/run_langfuse_faithfulness.py --seed-dataset

Requires LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY for --seed-dataset.
Faithfulness scoring is configured in the Langfuse UI (sampled / nightly).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "golden" / "retrieval.jsonl"
DATASET_NAME = "dashnote-retrieval-goldens"

UI_STEPS = """
Langfuse UI — sampled faithfulness (operator / nightly only)
============================================================
1. Open your Langfuse project → Datasets.
2. Create dataset `{dataset}` (or reuse after --seed-dataset).
3. Add an LLM-as-judge evaluator named `faithfulness`:
     - Input: user question + generated answer + retrieved context
     - Output: 0/1 or 0–1 score vs whether the answer is supported by context
     - Sampling: 5–10% of traces, or run as a nightly experiment (not per request)
4. Seed items from retrieval goldens (query_text + expect_content_markers).
5. Attach the evaluator to a dataset run or to `rag.answer` / `agent.turn` traces.
6. Record PASS: X/Y or judge mean in docs/EXPERIMENTS.md with environment=lab.
7. Do NOT add this script to .github/workflows/ci.yml.
""".strip()


def _load_retrieval_goldens() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if not GOLDEN.exists():
        return cases
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(json.loads(line))
    return cases


def _print_ui_steps() -> None:
    print(UI_STEPS.format(dataset=DATASET_NAME))


def _seed_dataset() -> int:
    sys.path.insert(0, str(ROOT.parent / "src"))
    from observability.langfuse_client import get_langfuse_client

    client = get_langfuse_client()
    if client is None:
        print("Langfuse client unavailable — set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY.")
        print("No dataset was written. Use --ui-only for the operator checklist.")
        return 2

    cases = _load_retrieval_goldens()
    if not cases:
        print(f"No retrieval goldens at {GOLDEN}")
        return 1

    created = 0
    create_dataset = getattr(client, "create_dataset", None)
    create_item = getattr(client, "create_dataset_item", None)
    if not callable(create_dataset) or not callable(create_item):
        print("This Langfuse SDK build has no create_dataset helpers.")
        print("Create the dataset in the UI using the goldens below, then attach a faithfulness judge.")
        for case in cases:
            print(json.dumps({"id": case.get("id"), "query": case.get("query_text")}, default=str))
        _print_ui_steps()
        return 0

    try:
        create_dataset(name=DATASET_NAME)
    except Exception as exc:  # noqa: BLE001
        print(f"Dataset create skipped or already exists: {exc}")

    for case in cases:
        payload = {
            "dataset_name": DATASET_NAME,
            "input": {"query_text": case.get("query_text"), "id": case.get("id")},
            "expected_output": {
                "expect_content_markers": case.get("expect_content_markers"),
                "expect_min_hits": case.get("expect_min_hits"),
            },
            "metadata": {"theme": case.get("theme"), "fixture_ref": case.get("fixture_ref")},
        }
        try:
            create_item(**payload)
            created += 1
        except TypeError:
            try:
                create_item(
                    dataset_name=DATASET_NAME,
                    input=payload["input"],
                    expected_output=payload["expected_output"],
                )
                created += 1
            except Exception as exc:  # noqa: BLE001
                print(f"Item skip {case.get('id')}: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"Item skip {case.get('id')}: {exc}")

    try:
        client.flush()
    except Exception:
        pass

    print(f"Seeded {created}/{len(cases)} items into dataset `{DATASET_NAME}`.")
    _print_ui_steps()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Operator Langfuse dataset / faithfulness helper (not CI)."
    )
    parser.add_argument(
        "--ui-only",
        action="store_true",
        help="Print Langfuse UI steps; do not call the API.",
    )
    parser.add_argument(
        "--seed-dataset",
        action="store_true",
        help="Upsert retrieval goldens into a Langfuse dataset when keys are set.",
    )
    args = parser.parse_args()
    if args.ui_only and not args.seed_dataset:
        _print_ui_steps()
        return 0
    if args.seed_dataset:
        return _seed_dataset()
    _print_ui_steps()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
