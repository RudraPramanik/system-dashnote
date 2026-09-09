# Chat / agent stream errors (LLM gone or hung)

**Status:** Fallback walks on HTTP 410 **and** wall-clock timeout (`unhang-agent-and-hitl`, 2026-09-09).  
**Symptom:** DashNotes Chat/Agent shows a blank reply or “Waiting for agent…” with no tokens. Notes, files, login, and `GET /health` still work.

Do **not** put API keys, JWT secrets, or user passwords in this file.

## What it is (and is not)

This is **not** an LLM boot race and **not** a frontend origin/CORS bug.

- Frontend `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1` correctly hits Compose nginx `:80`.
- `POST /ai/chat/stream` and `POST /ai/agent/stream` often return **HTTP 200**. The failure is an SSE `data: {"type":"error",...}` frame — or a quiet stream if the provider hung before the wall clock existed.
- Hard `GET /health` only checks Postgres + Redis. Soft `GET /health/ai` reports LLM as a **soft** dependency.

## Timeline

| When | Hosted model | Result |
|------|----------------|--------|
| 2026-08-07 | `nvidia_nim/mistralai/mistral-medium-3.5-128b` | NVIDIA NIM HTTP **410 Gone** (EOL) |
| 2026-08-21 | `nvidia_nim/z-ai/glm-5.2` (switched after the first EOL) | Same **410 Gone** (EOL 2026-08-21T09:00:00Z) |
| 2026-09-01 | `nvidia_nim/nvidia/nemotron-3-nano-30b-a3b` | **410 Gone** (EOL) |
| 2026-09-08 | fallback `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` | Hung ~20+ min; LiteLLM `timeout=` did not abort |

Pinning a single NIM id is not durable. Catalog listing also does not mean this account can call the id. Super 120B must not be the default safety net.

Embeddings (`gemini/gemini-embedding-2`) are a **separate** path. If `GEMINI_API_KEY` is invalid, new notes do not index (empty RAG). That is not the 410 stream error.

## Permanent behavior

1. `LLM_MODEL` is the first candidate. `LLM_MODEL_FALLBACKS` is a comma-separated list of extra LiteLLM ids.
2. Defaults (pinged live 2026-09-09): Nemotron 3.5 Lightning → `gemini/gemini-2.5-flash`. Super 120B is **not** a default hop.
3. On 410 / end-of-life / model not found **or** `AGENT_TOOL_TIMEOUT` wall clock, chat, agent, tool-side RAG, and structured completions retry the **same payload** on the next candidate (including `stream=True`).
4. API and worker **soft-resolve** a winner at startup. Failure does not block boot.
5. `GET /health/ai` reports `dependencies.llm` (soft). `GET /health` still ignores LLM.
6. If every candidate fails, SSE `error.message` is `LLM temporarily unavailable; retry shortly`.
7. Nginx `/ai/` uses `proxy_read_timeout 180s` plus SSE comment heartbeats so a slow first token is not dropped silently.

Code: `src/shared/llm/fallback.py`. Settings: `LLM_MODEL`, `LLM_MODEL_FALLBACKS`, `AGENT_TOOL_TIMEOUT`.

## Operator steps after pulling this change

```powershell
cd dashnotesystemv1
# Optional: set a live primary so the first hop is cheap
# LLM_MODEL=nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b
# LLM_MODEL_FALLBACKS=gemini/gemini-2.5-flash
docker compose up -d --build api worker nginx
```

Check:

```powershell
curl.exe http://127.0.0.1/health
curl.exe http://127.0.0.1/health/ai
```

`/health/ai` should include `"llm":{"reachable":true,...}`. Then send a Chat message in DashNotes. Agent `create_note` pauses for in-thread Approve/Reject.

If embeddings fail, replace `GEMINI_API_KEY` with a Google AI Studio key that accepts `gemini-embedding-2`. Do not change embedding dimension without re-indexing Qdrant.

## What not to do

- Do not treat “Docker is up” or `/health` 200 as proof that chat works.
- Do not scrape NVIDIA `/v1/models` as the only resolver (listed ≠ entitled).
- Do not collapse `/ai/chat*` into `/ai/agent*`.
- Do not put Super 120B or Ultra on the default fallback path.
