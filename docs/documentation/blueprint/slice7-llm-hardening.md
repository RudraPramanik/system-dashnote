# Slice 7.5 — Automation LLM Hardening (Recovery Blueprint)
## Cursor prompts to fix flaky `generate_note_tags`, `generate_file_metadata`, and agent tool loops

> **Status: ✅ COMPLETE** — implemented in `src/shared/llm/` (`structured.py`, `retry.py`, `env.py`). Kept as historical reference and gate criteria.
> **Next slice:** [Slice 7P — Production Platform](slice-platform.md) (prod compose, CI/CD, VPS deploy).

> **Context:** Slice 7 wiring is correct (events → worker fan-out → DB/Qdrant). Live failures were **LLM reliability**, not missing tasks or broken pipelines.
> **Prerequisite:** Slices 1–7 implemented per `ai.md` / `system.md`.
> **Related:** `slice7.md` (original automation build) · `ai.md` §Slice 7.5 · `observe.md`

---

## Executive diagnosis (2026-06-09)

### API key verdict — **key is valid; quota is the bottleneck**

Diagnostic run inside the running `api` container (`PYTHONPATH=/app/src`, same `from config import settings` path as `alembic/env.py`):

| Test | Model | Result |
|------|-------|--------|
| Embedding | `gemini/gemini-embedding-2` | **PASS** — dim 3072 |
| Plain completion | `gemini/gemini-2.5-flash` | **FAIL** — 503 UNAVAILABLE (high demand) |
| Structured completion | `gemini/gemini-2.5-flash` | **FAIL** — 429 RESOURCE_EXHAUSTED |
| Burst (5× completion) | `gemini/gemini-2.5-flash` | **0/5** — all 429 |

**429 detail from Google:**

```
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests
limit: 20, model: gemini-2.5-flash
quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier
```

### Do you need a new API key?

| Situation | Action |
|-----------|--------|
| Same Google Cloud project, free tier, heavy dev/testing | **No new key needed** — enable billing or wait for daily quota reset |
| Want reliable automation in dev | **Enable billing** on [Google AI Studio](https://aistudio.google.com/) for the existing project, **or** add `OPENAI_API_KEY` and set `LLM_MODEL=openai/gpt-4.1-mini` (or similar) in `.env` |
| Key revoked / wrong project | Create new key in AI Studio → update `GEMINI_API_KEY` in `.env` → `docker compose up -d --build api worker` |
| Production | Paid tier + code hardening below (retries alone cannot fix 20 req/day cap) |

**`alembic/env.py` note:** Alembic imports `from config import settings` after adding `src/` to `sys.path` — it loads the **same** `.env` as API/worker. A migration failure is unrelated to Gemini; this diagnostic confirms config loading is consistent across Alembic, API, and worker.

### Observed failure modes in worker logs

| Task | Error | Category |
|------|-------|----------|
| `generate_note_tags` | `Invalid JSON: expected value at line 1` / truncated JSON | **Parsing** — Gemini preamble or cut-off response |
| `generate_file_metadata` | `503 UNAVAILABLE` / `429 RESOURCE_EXHAUSTED` | **Quota / transient** |
| Agent `call_model` (2nd turn) | `503` / `429` after tool call | **Quota + no retry** |
| `embed_note_task` | Usually succeeds | Embeddings on separate quota (still works at 3072 dim) |

**Conclusion:** Fix in two layers — **(A) provider capacity** (billing or fallback model) and **(B) code resilience** (shared LLM client, retries, JSON salvage, ARQ re-queue).

---

## Readiness gate (run before Sub-step 7.5.1)

| Check | Command | Pass criteria |
|-------|---------|---------------|
| Stack up | `docker compose ps` | `api`, `worker`, `redis`, `db`, `qdrant` running |
| Config loads | `python -c "import sys; sys.path.insert(0,'src'); from config import settings; print(settings.ai_enabled)"` | `True` |
| Embedding works | See validation script in §Validation | dim 3072 |
| LLM quota headroom | Burst test in §Validation | ≥3/5 completions OK **or** billing enabled |
| Unit tests green | `python -m pytest tests/worker/test_automation_decision.py tests/shared/test_parsers.py -q` | all pass |

**Verdict:** Do not start code changes until provider quota is understood. Code hardening helps 503/transient errors and JSON parsing; it **cannot** overcome a hard 20 req/day free-tier cap without billing or a second provider.

---

## ARCHITECTURE LAW
### Paste as your FIRST message in every Cursor Composer session for 7.5.

```
ARCHITECTURE LAW — Slice 7.5 Automation LLM Hardening

GOAL:
  Make generate_note_tags, generate_file_metadata, and AutomationDecisionEngine
  share one resilient LiteLLM call path. Agent call_model should reuse the same retry policy.

NEW MODULE (allowed):
  src/worker/automation/llm.py  — AutomationLLMClient (or shared/worker/llm.py if reused by agent later)
  Import law: litellm, pydantic, config, tenacity, stdlib only.
  No FastAPI. No SQLAlchemy. No repositories.

EXISTING CODE — MODIFY IN PLACE:
  src/worker/automation/tasks.py     — replace inline litellm.acompletion with shared client
  src/worker/automation/decision.py  — replace inline litellm.acompletion with shared client
  src/config.py                      — append-only new settings (LLM_MAX_RETRIES, LLM_RETRY_MIN_WAIT, etc.)
  src/ai/workflows/workspace_assistant.py — call_model uses shared retry helper (import from worker layer FORBIDDEN in ai/*)

AGENT IMPORT LAW (Slice 6 still applies):
  src/ai/* cannot import src/worker/*.
  Extract retry + structured-parse helpers to src/shared/llm/ (preferred) so both worker and ai can import:
    shared/llm/structured.py  — parse_structured_response(), extract_json_blob()
    shared/llm/retry.py       — retry policy constants + is_retryable()
  shared/* may import: config, litellm, pydantic, tenacity, stdlib.

TASK BEHAVIOUR LAW:
  generate_note_tags / generate_file_metadata:
    - On transient failure after retries → log [AUTOMATION_LLM_RETRY_EXHAUSTED] and re-raise so ARQ retries the job
    - On permanent failure (auth, bad request) → log and return (no infinite ARQ loop)
    - On empty/invalid JSON after salvage → log [AUTOMATION_LLM_PARSE_FAIL] and re-raise (retryable)
  Never silently return on retryable errors — today tasks swallow exceptions and leave tags/summary empty.

ARQ LAW:
  Worker tasks that call LLM should raise on retryable failure so ARQ job_timeout + default retry applies.
  Document max_retries in worker/main.py job config if needed (arq supports max_tries per function).

COEXISTENCE:
  Do not change event bus, fan-out routing, or Slice 1 embed_note_task.
  Embedding retry stays in ai/embeddings/litellm_provider.py — do not merge embedding into automation LLM client.

SETTINGS (append to config.py):
  LLM_MAX_RETRIES: int = 4
  LLM_RETRY_MIN_WAIT: float = 2.0   # seconds — respect Retry-After from 429 when present
  LLM_RETRY_MAX_WAIT: float = 60.0
  LLM_STRUCTURED_MAX_TOKENS_TAGS: int = 256
  LLM_STRUCTURED_MAX_TOKENS_METADATA: int = 512
```

---

## Recovery plan — 4 sub-steps

### Sub-step 7.5.0 — Provider capacity (ops, no code)

**Goal:** Ensure LLM calls can succeed under normal dev load.

**Actions (pick one or combine):**

1. **Enable billing** on the Google AI project tied to `GEMINI_API_KEY` (removes 20 req/day flash cap).
2. **Add OpenAI fallback** in `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   LLM_MODEL=openai/gpt-4.1-mini
   ```
   Embeddings can stay on Gemini (`EMBEDDING_MODEL=gemini/gemini-embedding-2`) — separate quota.
3. **Throttle dev traffic:** avoid burst agent + automation on same minute during smoke tests.
4. **Optional:** second Gemini key in a separate project for worker-only (operational, not code).

**Validation:**
```powershell
docker compose exec -e PYTHONPATH=/app/src api python -c "
import asyncio, litellm
from config import get_settings
s=get_settings()
async def t():
    r=await litellm.acompletion(model=s.LLM_MODEL, messages=[{'role':'user','content':'PING'}], max_tokens=8, temperature=0)
    print('OK:', r.choices[0].message.content)
asyncio.run(t())
"
```

Pass: prints `OK: ...` without 429/503.

---

### Sub-step 7.5.1 — Shared structured LLM helper (`shared/llm/`)

**Goal:** One place for retries, JSON extraction, and Pydantic validation.

**Create:**

| File | Responsibility |
|------|----------------|
| `src/shared/llm/__init__.py` | exports `acompletion_structured` |
| `src/shared/llm/retry.py` | `_RETRYABLE_EXCEPTIONS` (mirror `litellm_provider.py`) |
| `src/shared/llm/structured.py` | `acompletion_structured(model, messages, schema: type[BaseModel], max_tokens, **kwargs) -> BaseModel` |

**`acompletion_structured` behaviour:**

1. Wrap `litellm.acompletion` with `tenacity` — same exception tuple as embeddings provider.
2. Pass `response_format=schema` to LiteLLM.
3. Parse response content:
   - Try `schema.model_validate_json(raw)`.
   - On failure: `extract_json_blob(raw)` — strip markdown fences, find first `{...}`, fix common Gemini preamble (`"Here is the JSON"`).
   - On second failure: raise `StructuredLLMParseError` (subclass of `ValueError`).
4. Log structured fields on success: `latency_ms`, `model`, `schema_name`, `retry_count`.

**Cursor prompt:**

```
Implement Sub-step 7.5.1 per docs/documentation/blueprint/slice7-llm-hardening.md.

Create src/shared/llm/ with retry.py, structured.py, __init__.py.
Mirror retry exceptions from src/ai/embeddings/litellm_provider.py.
Implement acompletion_structured() with tenacity and JSON salvage.
Add unit tests in tests/shared/test_llm_structured.py with mocked litellm (no real API calls):
  - valid JSON
  - JSON wrapped in markdown
  - preamble + JSON
  - truncated JSON → raises
  - retry on ServiceUnavailableError then success
Import law: config, litellm, pydantic, tenacity, stdlib only.
```

---

### Sub-step 7.5.2 — Wire automation tasks + decision engine

**Goal:** Replace three duplicate `litellm.acompletion` blocks with `acompletion_structured`.

**Modify:**

| File | Change |
|------|--------|
| `worker/automation/tasks.py` | `generate_file_metadata`, `generate_note_tags` → use `acompletion_structured`; **re-raise** retryable errors |
| `worker/automation/decision.py` | `evaluate_action` → use `acompletion_structured`; keep fail-safe block on permanent failure |

**Task error handling matrix:**

| Exception | `generate_*` behaviour | ARQ |
|-----------|------------------------|-----|
| `RateLimitError`, `ServiceUnavailableError`, `Timeout`, `APIConnectionError` | re-raise after retries | job retries |
| `StructuredLLMParseError` | re-raise (transient model glitch) | job retries |
| `AuthenticationError`, `NotFoundError` | log error, return | no retry |
| Success | commit DB, log `complete` | — |

**Log markers (for Grafana/alerts):**

| Marker | Meaning |
|--------|---------|
| `[AUTOMATION_LLM_RETRY_EXHAUSTED]` | All retries failed — transient |
| `[AUTOMATION_LLM_PARSE_FAIL]` | Could not parse structured output after salvage |
| `[AUTOMATION_LLM_AUTH_FAIL]` | Bad API key — ops action required |

**Cursor prompt:**

```
Implement Sub-step 7.5.2 per slice7-llm-hardening.md.

Refactor generate_note_tags and generate_file_metadata in worker/automation/tasks.py
to use shared.llm.acompletion_structured.
Refactor AutomationDecisionEngine.evaluate_action in worker/automation/decision.py similarly.
On retryable failures: re-raise so ARQ retries the job (stop swallowing exceptions).
Add tests/worker/test_automation_llm_tasks.py with mocked acompletion_structured.
Do not change fan-out routing or handle_file_uploaded extraction logic.
```

---

### Sub-step 7.5.3 — Agent `call_model` retry (Slice 6 touch)

**Goal:** Agent tool loops survive transient 503/429 on the second+ LLM turn.

**Modify:** `src/ai/workflows/workspace_assistant.py` — wrap `litellm.acompletion` in `shared/llm/retry.py` helper `acompletion_with_retry(...)` (non-structured).

**Route behaviour:** `ai_routes/agent.py` — map `ServiceUnavailableError` / `RateLimitError` after retries to **503** with message `"LLM temporarily unavailable; retry shortly"` instead of opaque 500.

**Cursor prompt:**

```
Implement Sub-step 7.5.3 per slice7-llm-hardening.md.

Add acompletion_with_retry to shared/llm/retry.py (messages + tools kwargs).
Use it in workspace_assistant.call_model.
In ai_routes/agent.py map exhausted retries to HTTP 503.
Add test in tests/ai/test_agent_retry.py mocking litellm (optional if time-boxed).
Preserve Slice 6 invariants in rules.md.
```

---

### Sub-step 7.5.4 — Config, docs, sign-off gate

**Append to `config.py`:** settings from Architecture Law.

**Update `ai.md` §Slice 7:** add bullet for `shared/llm/structured.py` and retry policy.

**Update `system.md` Testing:** add `tests/shared/test_llm_structured.py`.

**Sign-off gate:**

```powershell
# 1. Unit tests (no API)
python -m pytest tests/shared/test_llm_structured.py tests/worker/test_automation_decision.py -q

# 2. Provider smoke (needs quota headroom)
docker compose exec -e PYTHONPATH=/app/src api python -c "
import asyncio
from shared.llm.structured import acompletion_structured
from pydantic import BaseModel, Field
class T(BaseModel):
    tags: list[str] = Field(max_length=5)
async def main():
    r = await acompletion_structured(
        messages=[{'role':'user','content':'Title: Quantum\\n\\nEntanglement lab notes.'}],
        schema=T,
        max_tokens=128,
    )
    print('tags:', r.tags)
asyncio.run(main())
"

# 3. End-to-end automation
# Register → POST /notes/ → wait 30s → tags non-empty
# POST /files/upload (.txt) → wait 30s → summary non-empty
docker compose logs worker --tail 80 | Select-String "generate_note_tags complete|generate_file_metadata complete"

# 4. Agent tool loop
# POST /ai/agent {"message":"Search my notes for quantum and summarize."}
# Expect 200 or 503 (not 500) when quota exhausted

# 5. DB proof
docker compose exec db psql -U dashuser -d dashnotes -c \
  "SELECT title, tags FROM notes ORDER BY created_at DESC LIMIT 1;"
docker compose exec db psql -U dashuser -d dashnotes -c \
  "SELECT name, length(summary), tags FROM files ORDER BY created_at DESC LIMIT 1;"
```

**Gate pass criteria:**

| # | Criterion |
|---|-----------|
| 1 | All new unit tests pass |
| 2 | `acompletion_structured` smoke returns ≥1 tag |
| 3 | Worker logs show `generate_note_tags complete` and `generate_file_metadata complete` |
| 4 | Agent returns 200 with tool call **or** explicit 503 when provider down (never silent empty tags) |
| 5 | No regression: `embed_note_task`, RAG chat, test-search still work |

---

## What NOT to change

```
✗ Event types or bus routing (shared/events/)
✗ File extraction (FileParsingEngine) or index_file_chunks Qdrant path
✗ Slice 1 embed_note_task enqueue in notes/router.py
✗ RAG service / chat routes
✗ Neo4j / Slice 8 / multi-agent / Slice 9
✗ LangSmith enablement (Slice 10)
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Free tier 20 req/day | Billing or OpenAI fallback (7.5.0) |
| ARQ infinite retry on bad prompt | Cap `max_tries` on `generate_note_tags` / `generate_file_metadata` (e.g. 3) |
| JSON salvage masks model bugs | Log raw response on `[AUTOMATION_LLM_PARSE_FAIL]` at WARNING |
| Worker + agent compete for quota | Stagger tests; consider separate LLM_MODEL for worker in .env |
| Gemini 2.5 Flash demand spikes | Retry with backoff; optional fallback model env `LLM_FALLBACK_MODEL` (future) |

---

## Suggested implementation order

```
7.5.0 Ops (billing / fallback)     ← do first — unblocks validation
7.5.1 shared/llm structured helper
7.5.2 automation tasks + decision
7.5.3 agent call_model retry
7.5.4 config + docs + gate
```

**Estimated effort:** 1–2 focused sessions (code) + ops time for billing if on free tier.

---

## Quick reference — current vs target

| Area | Today | Target |
|------|-------|--------|
| LLM calls | Inline in 3 files, no retry | `shared/llm/acompletion_structured` |
| JSON errors | `model_validate_json` only | Salvage + retry |
| 429/503 | Swallowed → empty tags | Tenacity + ARQ retry + 503 to client (agent) |
| Embeddings | Retried in `litellm_provider.py` | Unchanged |
| API key | Valid, quota exhausted | Billing or second provider |

---

> **Next after gate:** Slice 10 (Observability — LangSmith flip, dashboards, runbooks). Slice 8 remains optional/skipped.
