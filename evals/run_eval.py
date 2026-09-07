#!/usr/bin/env python3
"""
Golden eval runner (Tier 0 / C-gate).

Modes:
  fixture — recorded responses under evals/fixtures/ (no live LLM keys)
  live    — HTTP calls to --base-url with Bearer token(s)

Usage (from repo root):
  set PYTHONPATH=src
  python evals/run_eval.py --mode fixture
  python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token <jwt>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent
GOLDEN_DIR = ROOT / "golden"
FIXTURE_DIR = ROOT / "fixtures"
DEFAULT_FILES = ("retrieval.jsonl", "tenant_isolation.jsonl", "agent_trajectory.jsonl")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if not path.exists():
        return cases
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(json.loads(line))
    return cases


def hit_texts(payload: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    results = payload.get("results")
    if results is None and isinstance(payload.get("raw"), list):
        results = payload["raw"]
    for hit in results or []:
        if not isinstance(hit, dict):
            continue
        chunk = hit.get("content_chunk") or {}
        text = chunk.get("text") or hit.get("chunk_text") or hit.get("text") or ""
        meta = hit.get("metadata") or {}
        title = meta.get("title") or hit.get("title") or ""
        texts.append(f"{title}\n{text}")
    return texts


def score_case(case: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str]:
    texts = hit_texts(payload)
    blob = "\n".join(texts)
    n = len(payload.get("results") or [])

    min_hits = case.get("expect_min_hits")
    if min_hits is not None and n < int(min_hits):
        return False, f"min_hits={min_hits} got={n}"

    max_hits = case.get("expect_max_hits")
    if max_hits is not None and n > int(max_hits):
        return False, f"max_hits={max_hits} got={n}"

    for marker in case.get("expect_content_markers") or []:
        if marker not in blob:
            return False, f"missing marker {marker!r}"

    for marker in case.get("expect_no_content_markers") or []:
        if marker in blob:
            return False, f"leaked marker {marker!r}"

    return True, "ok"


def score_trajectory(case: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str]:
    """Assert required_tools / forbidden_tools / sequence_mode against observed tools."""
    tools = payload.get("tools")
    if not isinstance(tools, list):
        return False, "fixture missing tools list"
    observed = [str(t) for t in tools]

    for name in case.get("forbidden_tools") or []:
        if name in observed:
            return False, f"forbidden tool used: {name}"

    required = [str(t) for t in (case.get("required_tools") or [])]
    mode = (case.get("sequence_mode") or "subset").lower()
    if mode == "exact":
        if observed != required:
            return False, f"exact sequence want={required} got={observed}"
    else:
        # subset: required tools must appear in order as a subsequence
        if not required:
            return True, "ok"
        idx = 0
        for tool in observed:
            if idx < len(required) and tool == required[idx]:
                idx += 1
        if idx != len(required):
            return False, f"subset missing required={required} got={observed}"
    return True, "ok"


def normalize_search_payload(data: Any) -> dict[str, Any]:
    """Accept gateway list[dict] or legacy {results: [...]} shapes."""
    if isinstance(data, list):
        return {"results": data, "raw": data}
    if isinstance(data, dict):
        if "results" in data:
            return data
        return {"results": [data], "raw": [data]}
    return {"results": []}


def load_fixture(ref: str) -> dict[str, Any]:
    path = FIXTURE_DIR / ref
    if not path.exists():
        raise FileNotFoundError(f"fixture not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict) and "tools" in raw:
        return raw
    return normalize_search_payload(raw)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def live_seed_note(
    client: httpx.Client,
    headers: dict[str, str],
    seed: dict[str, Any],
) -> None:
    nb = client.post("/notebooks/", headers=headers, json={"name": f"Eval NB {uuid.uuid4().hex[:6]}"})
    nb.raise_for_status()
    note = client.post(
        "/notes/",
        headers=headers,
        json={
            "title": seed.get("title") or "Eval note",
            "content": seed.get("content") or "",
            "is_private": bool(seed.get("is_private", False)),
        },
    )
    note.raise_for_status()
    wait = int(seed.get("wait_embed_sec") or 0)
    if wait > 0:
        time.sleep(wait)


def live_search(
    client: httpx.Client,
    headers: dict[str, str],
    case: dict[str, Any],
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": case["query_text"],
        "limit": int(case.get("limit") or 5),
    }
    if case.get("forged_workspace_probe"):
        # Must be ignored — workspace comes from JWT only.
        params["workspace_id"] = "999999"
    resp = client.get("/ai/test-search", headers=headers, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"test-search {resp.status_code}: {resp.text[:240]}")
    return normalize_search_payload(resp.json())


def pick_token(case: dict[str, Any], token_a: str | None, token_b: str | None) -> str | None:
    actor = (case.get("actor") or "a").lower()
    if actor == "b":
        return token_b or token_a
    return token_a


def run_cases(
    *,
    mode: str,
    cases: list[dict[str, Any]],
    base_url: str,
    token_a: str | None,
    token_b: str | None,
    seed_live: bool,
) -> tuple[int, int, list[str]]:
    passed = 0
    failed_ids: list[str] = []
    skipped = 0
    client: httpx.Client | None = None
    if mode == "live":
        client = httpx.Client(base_url=base_url.rstrip("/"), timeout=60.0)
        if seed_live and token_a:
            # Seed unique notes once, then one shared embed wait (max of waits).
            assert client is not None
            headers = auth_headers(token_a)
            max_wait = 0
            seen: set[str] = set()
            for case in cases:
                seed = case.get("seed")
                if not seed:
                    continue
                key = f"{seed.get('title')}|{seed.get('content')}"
                if key in seen:
                    continue
                seen.add(key)
                live_seed_note(client, headers, {**seed, "wait_embed_sec": 0})
                max_wait = max(max_wait, int(seed.get("wait_embed_sec") or 0))
            if seen and max_wait > 0:
                print(f"  ... seeded {len(seen)} notes; waiting {max_wait}s for embeds")
                time.sleep(max_wait)

    try:
        for case in cases:
            cid = case.get("id", "<missing-id>")
            hint = case.get("mode_hint", "either")
            skip_modes = set(case.get("skip_if_modes") or [])
            if mode in skip_modes:
                skipped += 1
                print(f"  SKIP  {cid}: skip_if_modes")
                continue
            if hint not in ("either", mode):
                skipped += 1
                print(f"  SKIP  {cid}: mode_hint={hint}")
                continue

            try:
                if mode == "fixture":
                    ref = case.get("fixture_ref")
                    if not ref:
                        raise RuntimeError("fixture mode requires fixture_ref")
                    payload = load_fixture(ref)
                else:
                    token = pick_token(case, token_a, token_b)
                    if not token:
                        raise RuntimeError("live mode requires --token (and --token-b for actor=b)")
                    assert client is not None
                    headers = auth_headers(token)
                    if case.get("theme") == "tenant_isolation" and case.get("actor") == "b" and not token_b:
                        skipped += 1
                        print(f"  SKIP  {cid}: live actor=b needs --token-b")
                        continue
                    if case.get("theme") == "agent_trajectory":
                        skipped += 1
                        print(f"  SKIP  {cid}: live trajectory not wired (use fixture)")
                        continue
                    payload = live_search(client, headers, case)

                if case.get("theme") == "agent_trajectory":
                    ok, detail = score_trajectory(case, payload)
                else:
                    ok, detail = score_case(case, payload)
                if ok:
                    passed += 1
                    print(f"  PASS  {cid}")
                else:
                    failed_ids.append(cid)
                    print(f"  FAIL  {cid}: {detail}")
            except Exception as exc:  # noqa: BLE001 — per-case isolation
                failed_ids.append(cid)
                print(f"  FAIL  {cid}: {exc}")
    finally:
        if client is not None:
            client.close()

    total = passed + len(failed_ids)
    if skipped:
        print(f"  ({skipped} skipped)")
    return passed, total, failed_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="DashNote golden eval runner")
    parser.add_argument("--mode", choices=("fixture", "live"), required=True)
    parser.add_argument("--base-url", default=os.environ.get("EVAL_BASE_URL", "http://127.0.0.1"))
    parser.add_argument("--token", default=os.environ.get("EVAL_TOKEN") or None)
    parser.add_argument("--token-b", default=os.environ.get("EVAL_TOKEN_B") or None)
    parser.add_argument(
        "--seed-live",
        action="store_true",
        help="For live retrieval cases with seed, create notes and wait for embed",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=list(DEFAULT_FILES),
        help="Golden JSONL filenames under evals/golden/",
    )
    args = parser.parse_args()

    cases: list[dict[str, Any]] = []
    for name in args.files:
        cases.extend(load_jsonl(GOLDEN_DIR / name))

    if not cases:
        print("No golden cases found.", file=sys.stderr)
        return 1

    print(f"=== Eval run mode={args.mode} cases={len(cases)} ===\n")
    if args.mode == "live" and not args.token:
        print("ERROR: --token required for live mode", file=sys.stderr)
        return 1

    passed, total, failed_ids = run_cases(
        mode=args.mode,
        cases=cases,
        base_url=args.base_url,
        token_a=args.token,
        token_b=args.token_b,
        seed_live=args.seed_live,
    )

    print(f"\nPASS: {passed}/{total}")
    if failed_ids:
        print("Failing:", ", ".join(failed_ids))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
