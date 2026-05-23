#!/usr/bin/env python3
"""
End-to-end smoke test against a running Docker stack (nginx :80 or API :8000).

Usage:
  python scripts/e2e_docker_smoke.py
  python scripts/e2e_docker_smoke.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_BASE = "http://127.0.0.1"
AI_WAIT_SEC = 45
SEARCH_QUERY = "quantum entanglement laboratory"


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


def _auth(headers: dict[str, str]) -> dict[str, str]:
    return headers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--ai-wait", type=int, default=AI_WAIT_SEC)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    run_id = uuid.uuid4().hex[:8]
    email = f"e2e-{run_id}@example.com"
    password = "E2eTestPass123!"
    ws_name = f"E2E Workspace {run_id}"

    r = Results()
    print(f"\n=== DashNote E2E smoke ({base}) ===\n")

    with httpx.Client(base_url=base, timeout=60.0) as client:
        # Health
        try:
            resp = client.get("/health")
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                r.ok("GET /health")
            else:
                r.fail("GET /health", f"{resp.status_code} {resp.text[:200]}")
        except Exception as e:
            r.fail("GET /health", str(e))
            print("\nAborting: API unreachable.")
            return 1

        # Register
        reg = client.post(
            "/auth/register",
            json={"email": email, "password": password, "workspace_name": ws_name},
        )
        if reg.status_code != 200:
            r.fail("POST /auth/register", f"{reg.status_code} {reg.text}")
            return 1
        tokens = reg.json()
        access = tokens["access_token"]
        refresh = tokens["refresh_token"]
        headers = {"Authorization": f"Bearer {access}"}
        r.ok("POST /auth/register")

        # Login
        login = client.post("/auth/login", json={"email": email, "password": password})
        if login.status_code == 200:
            r.ok("POST /auth/login")
        else:
            r.fail("POST /auth/login", f"{login.status_code} {login.text}")

        # Workspace
        ws = client.get("/workspaces/me", headers=headers)
        if ws.status_code == 200:
            ws_body = ws.json()
            workspace_id = ws_body.get("id")
            r.ok("GET /workspaces/me")
        else:
            r.fail("GET /workspaces/me", f"{ws.status_code} {ws.text}")
            workspace_id = None

        # Notebook
        nb = client.post("/notebooks/", headers=headers, json={"name": "E2E Notebook"})
        if nb.status_code == 200:
            notebook_id = nb.json()["id"]
            r.ok("POST /notebooks/")
        else:
            r.fail("POST /notebooks/", f"{nb.status_code} {nb.text}")
            notebook_id = None

        nb_list = client.get("/notebooks/", headers=headers)
        if nb_list.status_code == 200 and isinstance(nb_list.json(), list):
            r.ok("GET /notebooks/")
        else:
            r.fail("GET /notebooks/", f"{nb_list.status_code}")

        # Notes — distinctive content for semantic search
        note_payloads = [
            {
                "title": "Quantum Lab Notes",
                "content": (
                    "# Quantum Lab Notes\n\n"
                    "Today we observed quantum entanglement in the laboratory "
                    "using paired photon sources and coincidence counters."
                ),
                "is_private": False,
            },
            {
                "title": "Private diary",
                "content": "This is a private member-only note about weekend plans.",
                "is_private": True,
            },
        ]
        note_ids: list[int] = []
        for payload in note_payloads:
            cr = client.post("/notes/", headers=headers, json=payload)
            if cr.status_code == 200:
                note_ids.append(cr.json()["id"])
            else:
                r.fail("POST /notes/", f"{cr.status_code} {cr.text}")
                break
        else:
            r.ok(f"POST /notes/ ({len(note_ids)} notes)")

        notes_list = client.get("/notes/", headers=headers)
        if notes_list.status_code == 200 and len(notes_list.json()) >= len(note_ids):
            r.ok("GET /notes/")
        else:
            r.fail("GET /notes/", f"{notes_list.status_code} count={len(notes_list.json()) if notes_list.status_code==200 else '?'}")

        if note_ids:
            detail = client.get(f"/notes/{note_ids[0]}", headers=headers)
            if detail.status_code == 200:
                r.ok(f"GET /notes/{note_ids[0]}")
            else:
                r.fail("GET /notes/{id}", f"{detail.status_code}")

            patch = client.patch(
                f"/notes/{note_ids[0]}",
                headers=headers,
                json={"title": "Quantum Lab Notes (updated)"},
            )
            if patch.status_code == 200:
                r.ok(f"PATCH /notes/{note_ids[0]}")
            else:
                r.fail("PATCH /notes/{id}", f"{patch.status_code}")

        # Files (empty list is OK)
        files_resp = client.get("/files/", headers=headers)
        if files_resp.status_code == 200:
            body = files_resp.json()
            if isinstance(body, dict) and "items" in body:
                r.ok("GET /files/")
            else:
                r.fail("GET /files/", f"unexpected shape: {type(body)}")
        else:
            r.fail("GET /files/", f"{files_resp.status_code} {files_resp.text[:120]}")

        # Members (owner sees self)
        mem = client.get("/workspaces/members/", headers=headers)
        if mem.status_code == 200 and isinstance(mem.json(), list) and len(mem.json()) >= 1:
            r.ok("GET /workspaces/members/")
        else:
            r.fail("GET /workspaces/members/", f"{mem.status_code} {mem.text[:120]}")

        # Token refresh
        ref = client.post("/auth/refresh", json={"refresh_token": refresh})
        if ref.status_code == 200 and ref.json().get("access_token"):
            headers = {"Authorization": f"Bearer {ref.json()['access_token']}"}
            r.ok("POST /auth/refresh")
        else:
            r.fail("POST /auth/refresh", f"{ref.status_code}")

        # AI test-search
        print(f"\n  ... waiting {args.ai_wait}s for embed worker ...\n")
        time.sleep(args.ai_wait)

        ai_probe = client.get("/ai/test-search", params={"q": "probe"})
        if ai_probe.status_code == 401:
            r.ok("GET /ai/test-search (requires auth)")
        elif ai_probe.status_code == 503:
            detail = ai_probe.json().get("detail", ai_probe.text)
            r.skip("GET /ai/test-search", f"503 — {detail}")
        else:
            r.fail("GET /ai/test-search unauthenticated", f"expected 401, got {ai_probe.status_code}")

        search = client.get(
            "/ai/test-search",
            headers=headers,
            params={"q": SEARCH_QUERY, "limit": 5},
        )
        if search.status_code == 503:
            r.skip("GET /ai/test-search (authenticated)", search.json().get("detail", search.text))
        elif search.status_code != 200:
            r.fail("GET /ai/test-search (authenticated)", f"{search.status_code} {search.text[:300]}")
        else:
            hits = search.json()
            if not isinstance(hits, list):
                r.fail("GET /ai/test-search", "response is not a list")
            elif len(hits) == 0:
                r.fail(
                    "GET /ai/test-search",
                    "no results — worker may not have indexed (check GEMINI/OPENAI key and worker logs)",
                )
            else:
                top = hits[0]
                score = top.get("score", 0)
                wid_match = workspace_id is None or str(top.get("workspace_id")) == str(workspace_id)
                if wid_match:
                    r.ok(f"GET /ai/test-search ({len(hits)} hits, top score={score:.3f})")
                else:
                    r.fail(
                        "GET /ai/test-search tenant isolation",
                        f"workspace_id mismatch: {top.get('workspace_id')} != {workspace_id}",
                    )
                if score < 0.3:
                    r.fail("AI relevance gate", f"top score {score:.3f} < 0.3")

        # Second workspace tenant isolation
        email2 = f"e2e-b-{run_id}@example.com"
        reg2 = client.post(
            "/auth/register",
            json={"email": email2, "password": password, "workspace_name": f"Other WS {run_id}"},
        )
        if reg2.status_code == 200:
            h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
            iso = client.get("/ai/test-search", headers=h2, params={"q": SEARCH_QUERY, "limit": 5})
            if iso.status_code == 503:
                r.skip("tenant isolation search", "AI disabled")
            elif iso.status_code == 200:
                other_hits = iso.json()
                leaked = [
                    h for h in other_hits if workspace_id and str(h.get("workspace_id")) == str(workspace_id)
                ]
                if leaked:
                    r.fail("tenant isolation", f"other workspace saw {len(leaked)} hits from ws {workspace_id}")
                else:
                    r.ok("tenant isolation (other workspace empty or own only)")
            else:
                r.fail("tenant isolation request", f"{iso.status_code}")
        else:
            r.skip("tenant isolation", "second register failed")

        # Cleanup then logout
        if note_ids:
            del_resp = client.delete(f"/notes/{note_ids[0]}", headers=headers)
            if del_resp.status_code == 204:
                r.ok(f"DELETE /notes/{note_ids[0]}")
            else:
                r.fail("DELETE /notes/{id}", f"{del_resp.status_code}")

        logout = client.post("/auth/logout", headers=headers, json={})
        if logout.status_code == 204:
            r.ok("POST /auth/logout")
        else:
            r.fail("POST /auth/logout", f"{logout.status_code}")

    print(f"\n=== Summary: {len(r.passed)} passed, {len(r.failed)} failed, {len(r.skipped)} skipped ===\n")
    if r.failed:
        for f in r.failed:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
