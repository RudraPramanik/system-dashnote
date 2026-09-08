## Why

The workspace agent can sit for tens of minutes with no tokens after a user asks it to create a note from an uploaded PDF. Tonight that was a hung NVIDIA NIM call: primary `nemotron-3-nano-30b-a3b` is HTTP 410 Gone, fallback `nemotron-3-super-120b-a12b` never returned, `AGENT_TOOL_TIMEOUT=30` did not abort, Gemini Flash never ran because fallback only walks on model-gone, nginx/SSE went quiet, and even a healthy turn cannot finish `create_note` because DashNotes ignores `approval_required`. This must be fixed before VPS so chat and agent stay usable when hosted NIM ids die or stall.

## What Changes

- Retire dead/heavy default candidates. Default primary becomes a live **small** NVIDIA NIM id (`nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` after an apply-time ping). Immediate fallback is **`gemini/gemini-2.5-flash`** (Gemini key already present). Drop Super 120B and Ultra from the default path. If Lightning 410s/404s for this account, Gemini becomes primary.
- Walk the candidate list on **timeout / hang / retry-exhausted**, not only HTTP 410 / not-found. Enforce a real wall-clock (`asyncio.wait_for` using `AGENT_TOOL_TIMEOUT`) around completions, including RAG inside agent tools. LiteLLM `timeout=` alone is not sufficient.
- Disable Nemotron-style long “thinking” traces on chat/agent/automation completions (`LLM_MAX_TOKENS` stays the cap).
- Keep agent SSE alive through nginx: heartbeat comments plus `proxy_read_timeout` / `proxy_send_timeout` on `/ai/*`. If a stream ends with no tokens and no `error`/`done`/`approval_required`, the documented client MUST show a visible failure (not a blank bubble).
- Keep API-first HITL (interrupt before `create_note` / `update_note`). Do **not** auto-approve. Wire DashNotes in-thread Approve/Reject against existing `POST /ai/agent/resume` and `POST /ai/agent/reject` (sibling `dashnotes` app; this repo updates `frontendguide.md` as the contract).
- Tests and operator docs must cover fallback-on-timeout, HITL approve/reject, and stream-error copy. No live provider calls in CI. LLM remains a **soft** dependency (`GET /health` stays Postgres + Redis).

**Not BREAKING.** No route removals. `/ai/chat*` and `/ai/agent*` continue to coexist. Tenant identity still comes from JWT / `RequestContext` only.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `llm-resilience`: Fallback MUST trigger on wall-clock timeout and hang, not only model-gone. Default candidate list MUST prefer a live small NIM then Gemini Flash; 120B MUST NOT be a default hop. Completions used by chat, agent planner, and tool-side RAG MUST share that policy.
- `agent-hitl`: Product agent UI MUST handle `approval_required` with same-workspace Approve/Reject. API-first script/tests remain required. Auto-approve and skipping interrupt are out of scope.
- `frontend-developer-guide`: Agent SSE contract MUST include `approval_required`, resume/reject, heartbeat/quiet-stream failure UX, and MUST NOT treat a closed empty stream as success.

## Impact

- **Code (this repo):** `src/config.py` (append-only defaults), `src/shared/llm/fallback.py` + retry, `src/ai/services/rag_service.py`, `src/ai/workflows/workspace_assistant.py`, `src/ai_routes/agent.py` / `chat.py` (SSE heartbeat), `nginx/default.conf`, docs (`ai.md`, `nvidia.md`, `issue_solve.md`, `frontendguide.md`), `.env.example`. Local `.env` model ids (operator-owned; no secrets in git).
- **Code (sibling DashNotes):** `lib/hooks/ai/use-agent-stream.ts` and agent UI — in-thread Approve/Reject; empty-stream error. Recorded here because that is the user-visible HITL gap; implementation is in `../dashnotes`.
- **APIs:** Existing `/ai/agent`, `/ai/agent/stream`, `/ai/agent/resume`, `/ai/agent/reject` — no new mutation routes. Locked `approval_required` shape unchanged.
- **Tenancy / RBAC:** Unchanged. Resume/reject still re-validate checkpoint `workspace_id` from JWT. Qdrant wrappers and chat≠agent laws unchanged.
- **Soft vs hard deps:** LLM stays soft. Nginx timeout is edge config, not a new hard health check.
- **Tests:** `tests/shared/` and `tests/ai/` with mocked LiteLLM (timeout then fallback; 410 then Gemini). Existing HITL tests stay. Optional live ping via `scripts/test_nvidia_nim.py` during apply, not CI.
- **Non-goals:** Do not collapse `/ai/chat*` into `/ai/agent*`. Do not bypass `WorkspaceVectorSearch` / `NoteService`. Do not add a dedicated `files.summary` tool. Do not make LLM a hard `/health` dependency. Do not auto-create notes without HITL. No Alembic (no schema change).
