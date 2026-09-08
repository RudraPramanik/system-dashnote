## 1. Defaults and apply-time ping

- [x] 1.1 Ping `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` with `python scripts/test_nvidia_nim.py --model nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` (plain + tools). If 410/404, record Gemini Flash as primary for the rest of apply. Do not commit API keys.
- [x] 1.2 Update `src/config.py` defaults, `.env.example`, and local `.env` model ids to Lightning (or Gemini if ping failed) then `gemini/gemini-2.5-flash`. Remove Super 120B from documented defaults. Append-only; do not add unused settings.

## 2. Shared LLM wall-clock fallback (API + worker)

- [x] 2.1 In `src/shared/llm/fallback.py`, wrap each candidate invoke in `asyncio.wait_for` using `AGENT_TOOL_TIMEOUT`. On timeout, do not cache the id, cancel the task, and walk to the next candidate (same as 410). Tenacity retries for one candidate MUST fit inside that budget.
- [x] 2.2 Disable Nemotron thinking on `nvidia_nim/*` completions (`enable_thinking` false) while keeping `LLM_MAX_TOKENS`. Ensure structured completions (`shared/llm/structured.py`) and stream completions use the same wrapper.
- [x] 2.3 Route `RagService.answer` / `stream_answer` through `acompletion_with_fallback` with the wall clock so agent `search_notes` / `summarize_workspace` cannot hang past timeout. Do not bypass `WorkspaceVectorSearch`. Tracing stays in `observability.tracing`.
- [x] 2.4 Add tests in `tests/shared/test_llm_fallback.py`: mock a hung primary then success on Gemini; mock 410 then success; all candidates timeout yields `LLMUnavailableError`. Run `python -m pytest tests/shared/test_llm_fallback.py -q`.

## 3. Agent / chat SSE and nginx

- [x] 3.1 Emit SSE comment heartbeats (~15s) from `POST /ai/agent/stream` and `POST /ai/chat/stream` generators while waiting for the first real frame. Keep `X-Accel-Buffering: no`. Do not merge chat into agent.
- [x] 3.2 Add nginx `location /ai/` with `proxy_buffering off` and `proxy_read_timeout` / `proxy_send_timeout` of 180s in `nginx/default.conf`.
- [x] 3.3 Add or extend `tests/ai/` coverage that agent/chat stream error copy stays `LLM temporarily unavailable; retry shortly` when fallback exhausts. Run `python -m pytest tests/ai/test_agent_retry.py tests/ai/test_agent_hitl.py -q`.

## 4. Docs (this repo)

- [x] 4.1 Update `docs/nvidia.md`, `docs/documentation/issue_solve.md`, and `docs/documentation/ai.md` for Lightning → Gemini, timeout walk, and 120B-not-default.
- [x] 4.2 Update `docs/documentation/frontendguide.md`: `approval_required` fields, resume/reject bodies (JWT only, no `workspace_id`), empty-stream error UX, chat≠agent.

## 5. DashNotes HITL (sibling `../dashnotes`)

- [x] 5.1 Handle `approval_required` in `lib/hooks/ai/use-agent-stream.ts`: stop treating the tool as forever running; store pending tool/args/thread/interrupt.
- [x] 5.2 Add in-thread Approve/Reject calling `POST /ai/agent/resume` and `POST /ai/agent/reject` with `{ thread_id, interrupt_id? }` only. On success, show the JSON answer, toast, invalidate notes. Never auto-approve. Never send `workspace_id`.
- [x] 5.3 If the agent stream closes with no token, done, approval_required, or error, show the calm LLM-unavailable error instead of a blank bubble.

## 6. Validate

- [x] 6.1 Recreate `api`, `worker`, and `nginx` (`docker compose up -d --build api worker nginx`). Confirm `GET /health` still Postgres+Redis only and `GET /health/ai` remains soft.
- [x] 6.2 Re-run `python -m pytest tests/shared/test_llm_fallback.py tests/ai/test_agent_hitl.py tests/ai/test_agent_retry.py -q`.
- [x] 6.3 Manual: agent “create a note from the PDF/file summary” returns within the wall-clock budget (or Gemini fallback), shows Approve, approve creates the note; reject does not.
