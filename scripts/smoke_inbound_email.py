#!/usr/bin/env python3
"""Smoke: authenticated inbound email → note create (local compose / staging)."""

from __future__ import annotations

import argparse
import os
import sys
import uuid

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test inbound email ingest")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.getenv("INBOUND_API_KEY", ""))
    parser.add_argument("--from-email", default=os.getenv("INBOUND_SMOKE_EMAIL", ""))
    args = parser.parse_args()

    if not args.api_key:
        print("FAIL: set INBOUND_API_KEY or --api-key", file=sys.stderr)
        return 1
    if not args.from_email:
        print("FAIL: set INBOUND_SMOKE_EMAIL or --from-email", file=sys.stderr)
        return 1

    message_id = f"smoke-{uuid.uuid4()}"
    url = args.base_url.rstrip("/") + "/integrations/inbound/email"
    payload = {
        "message_id": message_id,
        "from_email": args.from_email,
        "subject": "Inbound smoke",
        "body": "Smoke test body from scripts/smoke_inbound_email.py",
        "attachments": [],
    }
    headers = {
        "Content-Type": "application/json",
        "X-Inbound-Api-Key": args.api_key,
    }

    with httpx.Client(timeout=30.0) as client:
        # Auth failure check
        bad = client.post(url, json=payload, headers={"Content-Type": "application/json"})
        if bad.status_code != 401 and bad.status_code != 503:
            print(f"FAIL: expected 401/503 without key, got {bad.status_code}", file=sys.stderr)
            return 1

        ok = client.post(url, json=payload, headers=headers)
        if ok.status_code != 200:
            print(f"FAIL: ingest {ok.status_code} {ok.text}", file=sys.stderr)
            return 1
        data = ok.json()
        if not data.get("note_id"):
            print(f"FAIL: missing note_id in {data}", file=sys.stderr)
            return 1

        dup = client.post(url, json=payload, headers=headers)
        if dup.status_code != 200 or not dup.json().get("duplicate"):
            print(f"FAIL: idempotent replay expected duplicate=true, got {dup.text}", file=sys.stderr)
            return 1

    print(f"PASS: note_id={data['note_id']} workspace_id={data.get('workspace_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
