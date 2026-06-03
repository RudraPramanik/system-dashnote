# DashNote Observability (agent context)

Short reference for humans and AI agents working on observability in this repo.

**Code layout:** `src/observability/`  
**Blueprint (full steps):** `src/docs/blueprint/observation-blueprint.md`

---

## Progress

| Step | What | Status |
|------|------|--------|
| 1 | JSON logging (`setup_logging` in `main.py` lifespan) | Done |
| 2 | Langfuse lazy client (`get_langfuse_client`) | Done |
| 3 | RAG traces in `RagService` | Done |
| 4 | Prometheus `/metrics` | Not started |
| 5–6 | Grafana + dashboards | Not started |

---

## Rules (do not break)

1. **`setup_logging()`** — only called in `src/main.py` lifespan (first line).
2. **`get_langfuse_client()`** — lazy only; **never** call from `main.py` lifespan (Step 3 tracing layer calls it).
3. **Langfuse SDK** — only imported in `src/observability/langfuse_client.py` and `tracing.py`. `RagService` uses `observability.tracing` only (no direct SDK).
4. **Imports:** `from config import get_settings` — never `from src.config`.
5. **LangSmith** — config exists; inactive. Langfuse is the active LLM trace path.

---

## Step 1 — JSON logging

- **Use:** `from observability import get_logger, setup_logging`
- **Schema:** `timestamp`, `level`, `logger`, `message` (+ optional `extra`: `request_id`, `workspace_id`, `user_id`, `route`, `latency_ms`)
- **Verify:** `docker compose logs --tail 20 api` → each line is JSON

---

## Step 2 — Langfuse client

### Config (`src/config.py`)

| Env var | Default | Purpose |
|---------|---------|---------|
| `LANGFUSE_PUBLIC_KEY` | `""` | Project public key (`pk-lf-...`) |
| `LANGFUSE_SECRET_KEY` | `""` | Secret key (`sk-lf-...`) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | EU cloud; US: `https://us.cloud.langfuse.com` |

**Enabled when:** both keys are non-empty → `settings.langfuse_enabled` is `True`.

Copy keys from Langfuse UI → Settings → API Keys. Put them in `.env` (not committed).

### Code

| File | Role |
|------|------|
| `src/observability/langfuse_client.py` | `get_langfuse_client()` — lazy singleton, never raises |
| `src/observability/__init__.py` | exports `get_langfuse_client` |

**Behaviour:**

- First call initializes once (`_initialized` flag).
- Missing keys → `None` + **warning** log (app keeps running).
- Bad keys / network error on init → `None` + **warning** log.
- Success → returns `Langfuse` instance + **info** log.

### Log messages (logger: `observability.langfuse_client`)

| Case | Level | Message |
|------|-------|---------|
| Keys missing | WARNING | `Langfuse disabled: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not both set` |
| Init failed | WARNING | `Langfuse client init failed; tracing unavailable` (+ `extra.error`, `extra.host`) |
| Init OK | INFO | `Langfuse client initialized` (+ `extra.host`) |

After Step 1 JSON logging is active, these appear as JSON lines with the same `message` string.

### Verify module loads

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH = "src"
pip install "langfuse>=2.60.0,<4" -q

# Import only (no client call)
python -c "from observability.langfuse_client import get_langfuse_client; print('PASS: import ok')"
```

### Verify missing keys

```powershell
$env:LANGFUSE_PUBLIC_KEY = ""
$env:LANGFUSE_SECRET_KEY = ""
python -c "
import importlib
import observability.langfuse_client as lc
importlib.reload(lc)
c = lc.get_langfuse_client()
assert c is None
print('PASS: client is None when disabled')
"
```

Expect WARNING with message containing `Langfuse disabled`.

### Verify with keys (optional)

Set real keys in `.env` or env vars, then:

```powershell
python -c "
from observability import setup_logging, get_langfuse_client
setup_logging()
client = get_langfuse_client()
print('client:', type(client).__name__ if client else None)
"
```

Expect INFO `Langfuse client initialized` and a `Langfuse` instance.

### Docker

Rebuild after `requirements/base.txt` change:

```powershell
docker compose build api
docker compose up -d api
```

API must start without calling `get_langfuse_client()` at boot.

---

## Step 3 — RAG tracing (`tracing.py` + `RagService`)

### Code

| File | Role |
|------|------|
| `src/observability/tracing.py` | `rag_trace`, `rag_span` — async context managers, no-op when Langfuse disabled |
| `src/observability/__init__.py` | exports `rag_trace`, `rag_span` |
| `src/ai/services/rag_service.py` | `answer()` and `stream_answer()` only |

**Behaviour:**

- Root observation name: `rag.answer` (metadata: `workspace_id`, `user_id`, `role`).
- Child spans: `retrieval` → `context_building` → `llm_generation` (generation type for LLM).
- Each span records `latency_ms` in output on exit; callers add domain fields via `span.update(output={...})`.
- `rag_trace` flushes the Langfuse client in `finally`; never raises.
- Langfuse Python SDK v4 uses `start_observation` under the hood (no direct `client.trace()`).

**`RagService` span outputs:**

| Span | Recorded output |
|------|-----------------|
| `retrieval` | `chunks_retrieved` |
| `context_building` | `chunks_used`, `char_budget` (`TOKEN_BUDGET_PER_REQUEST`) |
| `llm_generation` | `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost` (when LiteLLM returns them) + `latency_ms` |

Empty retrieval (no chunks): only `retrieval` span; trace still flushes.

### Verify module (no HTTP)

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH = "src"
python -c "from observability import rag_trace, rag_span; print('PASS')"
python -m ai.services.rag_service
```

### Trigger traces (requires JWT + Langfuse keys in `.env`)

```powershell
docker compose up -d --build api

# Non-streaming
curl.exe -sS -X POST http://127.0.0.1/ai/chat `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"What is in my notes?\"}"

# Streaming
curl.exe -sS -X POST http://127.0.0.1/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"Summarize my workspace notes.\"}" `
  --no-buffer
```

Replace `<TOKEN>` with a valid workspace JWT (same as Slice 3/4 gates in `src/docs/ai.md`).

### Langfuse UI checklist

After one `/ai/chat` and one `/ai/chat/stream` call:

1. Trace named **`rag.answer`** visible (Traces / Observations).
2. Three child spans: **`retrieval`**, **`context_building`**, **`llm_generation`**.
3. Each span output includes **`latency_ms`** (milliseconds).
4. **`retrieval`** output includes **`chunks_retrieved`** (integer).
5. **`context_building`** output includes **`chunks_used`** and **`char_budget`**.
6. **`llm_generation`** shows token fields when LiteLLM populates `response.usage` (and **`cost`** when `_hidden_params.response_cost` is set).
7. Trace input/metadata includes **`workspace_id`**, **`user_id`**, **`role`** (no raw JWT).

If keys are missing, the app runs normally; no traces are sent (no-op path).

---

## Next (Step 4)

- Prometheus `/metrics` on FastAPI (`main.py` only).

---

## Stack (target)

```
Nginx → FastAPI
          ├─ JSON logs (stdout)
          ├─ Langfuse (RAG/agent traces)
          └─ Prometheus → Grafana
```
