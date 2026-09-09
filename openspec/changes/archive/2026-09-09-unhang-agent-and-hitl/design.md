## Context

See `proposal.md` for why. Constraints that shape the approach:

- Completions already go through `shared.llm.fallback.acompletion_with_fallback` (410 walk) and `shared.llm.retry.acompletion_with_retry` (transient retries). Agent `call_model` passes `timeout=AGENT_TOOL_TIMEOUT`; RAG `RagService.answer` does not. LiteLLM’s `timeout=` did not abort NVIDIA NIM tonight.
- Agent runs **in the API process** (`POST /ai/agent*`), not ARQ. Worker uses the same LiteLLM helpers for tags/metadata. Chat stays on `/ai/chat*`.
- HITL interrupt + `/ai/agent/resume` (JSON `ainvoke`) and `/ai/agent/reject` already exist. DashNotes `use-agent-stream.ts` ignores `approval_required`. This repo has no frontend; sibling `../dashnotes` is the product UI. `frontendguide.md` is the client contract in this repo.
- Nginx `default.conf` has no `proxy_read_timeout`. DashNotes uses `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1`.
- Append-only settings. No Alembic. LLM stays a soft `/health` dependency. Qdrant search stays `WorkspaceVectorSearch`. Tools stay on `NoteService` / `RagService`. No Langfuse SDK in `src/ai/*`.

## Goals / Non-Goals

**Goals:**

- One completion wrapper owns wall-clock abort + candidate walk for chat, agent planner, tool-side RAG, and worker structured calls.
- Default candidate list is a live small NIM then Gemini Flash; 120B is not a default hop.
- SSE through nginx survives a quiet first hop; empty close is a visible error.
- HITL stays; DashNotes can Approve/Reject in-thread using existing JSON resume/reject.

**Non-Goals:**

- Streaming resume (`/ai/agent/resume/stream`).
- Auto-approve, env flag to skip interrupt, or an automation inbox.
- New `files.summary` tool or merging chat into agent.
- New timeout setting unless `AGENT_TOOL_TIMEOUT` cannot be reused without lying about name/docs.

## Decisions

### D1 — Wall clock lives in `acompletion_with_fallback`, not per-call LiteLLM `timeout=`

Wrap each candidate’s invoke in `asyncio.wait_for(..., timeout=settings.AGENT_TOOL_TIMEOUT)`. On `TimeoutError`, treat that id like a failed hop (log, do not cache as winner) and try the next candidate. Do **not** spend `LLM_MAX_RETRIES` × 30s on the same hung NIM; tenacity retries stay inside the wait_for budget for that candidate (or retry only RateLimit/connection errors that return quickly).

**Why:** Tonight `timeout=30` was already passed to LiteLLM and never fired. `asyncio.wait_for` is process-owned and matches the spec (“provider SDK timeouts alone MUST NOT be treated as sufficient”).

**Alternative considered:** `httpx` timeout only — rejected; NVIDIA path already ignored it. Per-node `wait_for` in `call_model` only — rejected; RAG inside tools would still hang.

Agent planner, `RagService.answer` / `stream_answer`, and structured worker completions MUST all call this wrapper (stream path included: wait_for on starting the stream + first-byte policy as implemented, but non-stream wait_for is the agent hang that bit us).

Cancel the inner task on timeout so NVIDIA work does not keep a coroutine forever after fallback starts.

### D2 — Default ids: Lightning then Gemini Flash; ping at apply, not in CI

`config.py` / `.env.example` defaults:

```
LLM_MODEL=nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b
LLM_MODEL_FALLBACKS=gemini/gemini-2.5-flash
```

Apply-time: run `scripts/test_nvidia_nim.py --model nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` (plain + tools). If 410/404, set primary to `gemini/gemini-2.5-flash` and keep fallbacks non-empty or a second Gemini id. Operator `.env` is updated the same way; never commit secrets.

Disable Nemotron thinking for these completions (`extra_body` / `chat_template_kwargs.enable_thinking=false` when the model is `nvidia_nim/*`), keep `LLM_MAX_TOKENS=2048`.

**Why:** Nano is EOL. Super 120B hung. Lightning is the current small agentic NIM; Gemini is already keyed for embeddings and was the unused last hop.

**Alternative considered:** Gemini-only primary — simpler, but the operator asked to keep free NIM when it works. 120B as fallback — rejected (this incident).

### D3 — SSE comments + nginx `/ai/` timeouts; resume stays JSON

- API: while waiting on `astream_events`, yield SSE comment heartbeats (`: keepalive\n\n`) on a ~15s interval so nginx `proxy_read_timeout` resets. Existing `X-Accel-Buffering: no` stays.
- Nginx: `location /ai/` with `proxy_read_timeout` and `proxy_send_timeout` at least `AGENT_TOOL_TIMEOUT` × candidate count (document 180s as a safe ceiling for two hops) plus `proxy_buffering off`.
- DashNotes: if the stream ends with none of `token` / `done` / `approval_required` / `error`, set the same calm error as LLM unavailable.

Resume/reject remain JSON (`ainvoke`). FE on Approve displays `AgentResponse.answer` (and toast/invalidate notes). No new route.

**Why:** Smallest change that matches “stream ends on approval, client reconnects.” Streaming resume would duplicate the stream contract.

**Alternative considered:** Hold SSE open until the user clicks Approve — rejected (proxy timeouts; Slice 8X.3 already closed the stream on purpose).

### D4 — HITL UI in sibling DashNotes; this repo owns the contract

Extend `use-agent-stream.ts` + a small in-thread card (tool name, title, truncated content, Approve/Reject). `POST /ai/agent/resume|reject` with `{ thread_id, interrupt_id? }` only. Update `docs/documentation/frontendguide.md` here. Keep `scripts/smoke_hitl.py` and `tests/ai/test_agent_hitl.py`.

**Why:** Backend HITL is done; the product bug is the missing client. Auto-approve would violate tenant-safe mutation control on VPS.

**Process ownership**

| Work | Process |
|------|---------|
| Candidate walk + wait_for | API + worker via `shared.llm` |
| Agent graph / HITL interrupt | API LangGraph tool node |
| Resume/reject mutations | API `NoteService` after checkpointer resume |
| File index/summary | ARQ worker (unchanged this change) |
| SSE heartbeat | API streaming generator |
| Proxy timeouts | nginx |
| Approve/Reject card | DashNotes (sibling) |

No Qdrant collection changes (`notes_chunks` / `files_chunks` unchanged).

## Risks / Trade-offs

- **[Risk] Lightning 410/404 or slow thinking anyway** → Mitigation: apply-time ping; Gemini next; thinking off; wait_for walks away in 30s.
- **[Risk] Cancelling a hung httpx/NIM task does not close the socket** → Mitigation: still start Gemini; log; process stays up (LLM soft).
- **[Risk] 30s × two candidates feels slow** → Mitigation: heartbeat + nginx; still bounded vs 20 minutes; do not retry the hung id four times.
- **[Risk] JSON resume is a second request; user might navigate away** → Mitigation: checkpoint already keyed by `thread_id`; card stays on the thread until approve/reject.
- **[Risk] OpenSpec apply root is this repo only** → Mitigation: tasks split “this repo” vs “sibling dashnotes”; do not skip the FE tasks.

## Migration Plan

1. Ping Lightning (tools). Set defaults + local `.env` ids. Recreate `api` + `worker` (`docker compose up -d --build api worker nginx`).
2. Ship fallback/wait_for + RAG timeout + heartbeat + nginx. Confirm `GET /health` unchanged; agent no longer silent-hangs when primary is stubbed to sleep in tests.
3. Ship DashNotes approval card. Smoke: PDF/file already indexed → agent “create a note from that summary” → Approve → note appears.
4. Rollback: revert image/env to previous candidate list; HITL API is backward compatible if FE is rolled back (stream still closes on `approval_required`).

## Open Questions

None that change specs. Lightning vs Gemini-as-primary is resolved at apply by ping, not by a later design change.
