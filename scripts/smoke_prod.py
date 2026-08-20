#!/usr/bin/env python3
"""
Lean production smoke (Slice 7P.6) — hard gate for deploy / CD.

Hard checks (must pass → exit 0):
  GET /health, auth (register or SMOKE_EMAIL/SMOKE_PASSWORD login),
  POST /notebooks/, POST /notes/

Soft checks (default off; never fail hard gate):
  GET /health/ai, optional small file upload + short poll
  Enable with --with-ai or SMOKE_SOFT_AI=1

Usage:
  python scripts/smoke_prod.py
  SMOKE_BASE_URL=http://127.0.0.1 python scripts/smoke_prod.py
  python scripts/smoke_prod.py --base-url https://api.example.com --with-ai

Broader local E2E remains scripts/e2e_docker_smoke.py — do not replace it.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_BASE = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1").rstrip("/")
SOFT_AI_ENV = os.environ.get("SMOKE_SOFT_AI", "").strip().lower() in {"1", "true", "yes"}
FILE_POLL_SEC = 30


@dataclass
class Results:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def ok(self, name: str) -> None:
        self.passed.append(name)
        print(f"  PASS  {name}")

    def fail(self, name: str, detail: str) -> None:
        self.failed.append(f"{name}: {detail}")
        print(f"  FAIL  {name}: {detail}")

    def skip(self, name: str, reason: str) -> None:
        self.skipped.append(f"{name}: {reason}")
        print(f"  SKIP  {name}: {reason}")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def hard_health(client: httpx.Client, r: Results) -> bool:
    try:
        resp = client.get("/health")
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        db_ok = bool(body.get("dependencies", {}).get("database", {}).get("reachable"))
        if resp.status_code == 200 and body.get("status") == "ok" and db_ok:
            r.ok("GET /health")
            return True
        r.fail("GET /health", f"{resp.status_code} {resp.text[:200]}")
        return False
    except Exception as exc:
        r.fail("GET /health", str(exc))
        return False


def hard_auth(client: httpx.Client, r: Results) -> str | None:
    email = os.environ.get("SMOKE_EMAIL", "").strip()
    password = os.environ.get("SMOKE_PASSWORD", "").strip()

    if email and password:
        login = client.post("/auth/login", json={"email": email, "password": password})
        if login.status_code == 200 and login.json().get("access_token"):
            r.ok("POST /auth/login")
            return login.json()["access_token"]
        r.fail("POST /auth/login", f"{login.status_code} {login.text[:200]}")
        return None

    run_id = uuid.uuid4().hex[:8]
    email = f"smoke-{run_id}@example.com"
    password = "SmokeTestPass123!"
    ws_name = f"Smoke Workspace {run_id}"
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": password, "workspace_name": ws_name},
    )
    if reg.status_code != 200 or not reg.json().get("access_token"):
        r.fail("POST /auth/register", f"{reg.status_code} {reg.text[:200]}")
        return None
    r.ok("POST /auth/register")
    return reg.json()["access_token"]


def hard_content(client: httpx.Client, headers: dict[str, str], r: Results) -> bool:
    nb = client.post("/notebooks/", headers=headers, json={"name": "Smoke Notebook"})
    if nb.status_code != 200:
        r.fail("POST /notebooks/", f"{nb.status_code} {nb.text[:200]}")
        return False
    r.ok("POST /notebooks/")

    note = client.post(
        "/notes/",
        headers=headers,
        json={
            "title": "Smoke note",
            "content": "# Smoke\n\nProduction smoke hard-gate note.",
            "is_private": False,
        },
    )
    if note.status_code != 200 or "id" not in note.json():
        r.fail("POST /notes/", f"{note.status_code} {note.text[:200]}")
        return False
    r.ok("POST /notes/")
    return True


def soft_ai_health(client: httpx.Client, r: Results) -> None:
    try:
        resp = client.get("/health/ai")
        body: dict[str, Any] = {}
        try:
            body = resp.json()
        except Exception:
            pass
        status_label = body.get("status", "?")
        if resp.status_code == 200:
            r.ok(f"GET /health/ai ({status_label})")
        else:
            r.skip("GET /health/ai", f"{resp.status_code} {resp.text[:160]}")
    except Exception as exc:
        r.skip("GET /health/ai", str(exc))


def soft_file_upload(client: httpx.Client, headers: dict[str, str], r: Results) -> None:
    """Optional: upload a tiny text file and briefly poll for worker fields."""
    try:
        files = {
            "file": ("smoke.txt", b"smoke soft-ai upload fixture\n", "text/plain"),
        }
        data = {"is_private": "false", "description": "smoke soft check"}
        up = client.post("/files/upload", headers=headers, files=files, data=data)
        if up.status_code != 200:
            r.skip("POST /files/upload", f"{up.status_code} {up.text[:160]}")
            return
        file_id = up.json().get("id")
        r.ok("POST /files/upload")
        if not file_id:
            r.skip("poll GET /files/{id}", "no file id")
            return

        deadline = time.time() + FILE_POLL_SEC
        while time.time() < deadline:
            detail = client.get(f"/files/{file_id}", headers=headers)
            if detail.status_code == 200:
                body = detail.json()
                if body.get("summary") or body.get("tags") or body.get("extracted_text"):
                    r.ok(f"GET /files/{file_id} (automation fields)")
                    return
            time.sleep(2)
        r.skip(
            f"GET /files/{file_id} poll",
            f"no summary/tags/extracted_text within {FILE_POLL_SEC}s",
        )
    except Exception as exc:
        r.skip("file soft check", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="Lean production smoke (7P.6 hard gate)")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE,
        help=f"API edge base URL (default: {DEFAULT_BASE} or SMOKE_BASE_URL)",
    )
    parser.add_argument(
        "--with-ai",
        action="store_true",
        default=SOFT_AI_ENV,
        help="Run soft AI checks (also SMOKE_SOFT_AI=1); never fails hard exit",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    r = Results()

    print(f"\n=== DashNote prod smoke ({base}) ===\n")

    with httpx.Client(base_url=base, timeout=60.0) as client:
        if not hard_health(client, r):
            print("\nAborting: hard health failed.")
            _summary(r)
            return 1

        token = hard_auth(client, r)
        if not token:
            _summary(r)
            return 1
        headers = _auth_headers(token)

        if not hard_content(client, headers, r):
            _summary(r)
            return 1

        if args.with_ai:
            print("\n  --- soft AI checks (non-blocking) ---\n")
            soft_ai_health(client, r)
            soft_file_upload(client, headers, r)
        else:
            r.skip("soft AI", "pass --with-ai or SMOKE_SOFT_AI=1 to enable")

    return _summary(r)


def _summary(r: Results) -> int:
    print(
        f"\n=== Summary: {len(r.passed)} passed, "
        f"{len(r.failed)} failed, {len(r.skipped)} skipped ===\n"
    )
    if r.failed:
        for item in r.failed:
            print(f"  • {item}")
        print()
        return 1
    print("HARD GATE: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
