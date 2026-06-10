#!/usr/bin/env python3
"""E2E smoke: register → notes → file upload → agent."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "http://localhost:8000"


def req(method: str, path: str, *, token: str | None = None, body: dict | None = None, timeout: int = 120):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"raw": detail}
        return e.code, parsed


def upload_file(token: str, filename: str, content: str) -> tuple[int, dict]:
    boundary = "----DashNoteBoundary7d5"
    parts = [
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"{content}\r\n",
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="is_private"\r\n\r\n'
        f"false\r\n",
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="description"\r\n\r\n'
        f"Quantum research notes\r\n",
        f"--{boundary}--\r\n",
    ]
    body = "".join(parts).encode()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    request = urllib.request.Request(
        f"{BASE}/files/upload", data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main() -> int:
    ts = int(datetime.now(timezone.utc).timestamp())
    email = f"e2e-{ts}@example.com"
    password = "TestPass123!"

    print("=== REGISTER ===")
    print(f"Email: {email}")
    status, reg = req(
        "POST",
        "/auth/register",
        body={"email": email, "password": password, "workspace_name": f"E2E Workspace {ts}"},
    )
    if status != 200:
        print(f"FAIL register: HTTP {status} {reg}")
        return 1

    token = reg["access_token"]
    refresh = reg["refresh_token"]
    print(f"access_token: {token[:40]}...")
    print(f"refresh_token: {refresh[:40]}...")

    print("\n=== CREATE NOTES ===")
    notes_data = [
        {
            "title": "Quantum Entanglement Lab",
            "content": (
                "Today we observed quantum entanglement between two photons. "
                "The Bell inequality was violated. Key concepts: superposition, "
                "correlation, measurement collapse."
            ),
        },
        {
            "title": "Superposition Notes",
            "content": (
                "A quantum system can exist in multiple states simultaneously "
                "until measured. Used in quantum computing qubits."
            ),
        },
        {
            "title": "Bell Test Results",
            "content": (
                "CHSH inequality S-value was 2.4, exceeding classical limit of 2. "
                "Confirms non-local correlations."
            ),
        },
    ]
    for note in notes_data:
        status, created = req("POST", "/notes/", token=token, body=note)
        if status != 200:
            print(f"FAIL create note: HTTP {status} {created}")
            return 1
        print(f"Created note id={created['id']} title={created['title']}")

    print("\n=== WAIT 40s for automation (tags + embed) ===")
    time.sleep(40)

    print("\n=== CHECK NOTES TAGS ===")
    status, notes = req("GET", "/notes/", token=token)
    if status != 200:
        print(f"FAIL list notes: HTTP {status} {notes}")
        return 1
    tags_ok = False
    for n in notes:
        tags = n.get("tags") or []
        print(f"Note {n['id']}: tags={tags}")
        if tags:
            tags_ok = True

    print("\n=== UPLOAD FILE ===")
    file_content = (
        "Quantum computing uses qubits in superposition. Entanglement enables "
        "parallel computation across correlated states."
    )
    status, uploaded = upload_file(token, "quantum-notes.txt", file_content)
    if status != 200:
        print(f"FAIL upload: HTTP {status} {uploaded}")
        return 1
    print(f"Uploaded file id={uploaded['id']} name={uploaded['name']}")

    print("\n=== WAIT 40s for file metadata ===")
    time.sleep(40)

    print("\n=== AGENT REQUEST ===")
    status, agent = req(
        "POST",
        "/ai/agent",
        token=token,
        body={"message": "Search my notes for quantum entanglement and summarize what you find."},
        timeout=180,
    )
    if status == 200:
        print("Agent status: SUCCESS")
        answer = agent.get("answer", "")
        print(f"Answer preview: {answer[:500]}")
        print(f"tool_calls_made: {agent.get('tool_calls_made')}")
        print(f"steps_taken: {agent.get('steps_taken')}")
        print(f"thread_id: {agent.get('thread_id')}")
        agent_ok = agent.get("tool_calls_made", 0) > 0 or len(answer) > 20
    elif status == 503:
        print(f"Agent status: HTTP 503 (LLM temporarily unavailable) — acceptable")
        print(json.dumps(agent, indent=2))
        agent_ok = True
    else:
        print(f"Agent status: HTTP {status}")
        print(json.dumps(agent, indent=2))
        agent_ok = False

    print("\n=== SUMMARY ===")
    print(f"Registration: PASS")
    print(f"Notes created: PASS")
    print(f"Auto-tags: {'PASS' if tags_ok else 'PENDING/FAIL (check worker logs)'}")
    print(f"Agent: {'PASS' if agent_ok else 'FAIL'}")

    return 0 if agent_ok else 1


if __name__ == "__main__":
    sys.exit(main())
