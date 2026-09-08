# DashNote Observability (agent context)

Short reference for humans and AI agents working on observability in this repo.

**Code layout:** `src/observability/`  
**Blueprint (full steps):** [blueprint/observation-blueprint.md](./blueprint/observation-blueprint.md)

---

## Progress

| Step | What | Status |
|------|------|--------|
| 1 | JSON logging (`setup_logging` in `main.py` lifespan) | Done |
| 2 | Langfuse lazy client (`get_langfuse_client`) | Done |
| 3 | RAG traces in `RagService` | Done |
| 4 | Prometheus `/metrics` | Done |
| 5 | Prometheus Compose (`:9090`) | Done (Grafana optional / not default Compose) |
| 6 | Grafana provisioning files (optional UI) | Done (files may exist; not required locally) |

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

Replace `<TOKEN>` with a valid workspace JWT.

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

## Step 4 — Prometheus HTTP metrics

### Dependency

`requirements/base.txt` (Docker image source):

```
prometheus-fastapi-instrumentator >= 0.11.0
```

Installed in API image: **7.1.0** (pulls `prometheus-client` transitively).

### Code (`src/main.py` only)

Instrumentation runs at the end of `create_app()`, after middleware, routes, and exception handlers — before the app serves traffic.

**Note (v7 API):** `metric_namespace` and `metric_subsystem` are passed to `.instrument()`, not `Instrumentator()`. Constructor options `should_group_status_codes` and `should_ignore_untemplated` are unchanged.

```python
from prometheus_fastapi_instrumentator import Instrumentator

# inside create_app(), before return app:
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
).instrument(
    app,
    metric_namespace="dashnote",
    metric_subsystem="api",
).expose(app, endpoint="/metrics")
```

### Metric prefix

All **HTTP metrics** from the instrumentator use the prefix **`dashnote_api_`** (namespace `dashnote` + subsystem `api`).

Standard process/Python metrics (`python_*`, `process_*`) have no application prefix — that is expected.

### Exact metric names (verified `curl http://localhost:8000/metrics`)

Use these names in Grafana/Prometheus queries (Step 6).

| Role | Exact name | Type |
|------|------------|------|
| Request total counter | `dashnote_api_http_requests_total` | counter |
| Latency histogram (handler labels; SLI dashboards) | `dashnote_api_http_request_duration_seconds` | histogram |
| Latency histogram (many buckets; percentiles) | `dashnote_api_http_request_duration_highr_seconds` | histogram |
| Request body size | `dashnote_api_http_request_size_bytes` | summary |
| Response body size | `dashnote_api_http_response_size_bytes` | summary |

**Step 6 defaults:**

- P95 latency: `histogram_quantile(0.95, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))`
- Request rate: `sum(rate(dashnote_api_http_requests_total[5m]))`
- Error rate (5xx): filter `dashnote_api_http_requests_total` with `status=~"5.."`

Labels on the counter/handler histogram: `handler`, `method`, `status` (status not grouped into families because `should_group_status_codes=False`).

### Verify

```powershell
cd g:\projects\dashnotesystemv1
docker compose up -d --build api

# Generate at least one request (optional but populates handler metrics)
curl.exe -sS http://localhost:8000/health

curl.exe -sS http://localhost:8000/metrics
```

Expect `# TYPE dashnote_api_http_requests_total counter` and histogram types for `dashnote_api_http_request_duration_*`.

### Rules

- No custom metrics in this step.
- Do not instrument in routers, services, or `src/observability/`.

---

## Step 5 — Prometheus (+ optional Grafana)

### Current local Compose

`docker-compose.yml` ships **`prometheus`** (`:9090`, 256m). It does **not** include a Grafana service. Scrape `api:8000` at `/metrics`.

| Path | Role |
|------|------|
| `monitoring/prometheus.yml` | Scrape `api:8000` at `/metrics`, 15s interval |
| `docker-compose.yml` | `prometheus` service only (no grafana) |
| `monitoring/grafana/provisioning/` | Optional leftover provisioning for Grafana Cloud or a manually added Grafana container |

### Prometheus config

- **Job:** `dashnote_api` → `http://api:8000/metrics`
- **Retention:** 7d (`--storage.tsdb.retention.time=7d`)
- **Image:** `prom/prometheus:v2.51.2`

### Grafana (optional — not default Compose)

Provisioning files under `monitoring/grafana/` may still exist for Grafana Cloud or a custom Compose service. Do **not** expect http://localhost:3001 from a plain `docker compose up`. Prefer Grafana Cloud remote_write in production (see `docker-compose.prod.yml` observability profile).

### Env (`.env.example`)

```env
# Optional — only if you add a Grafana container yourself
GRAFANA_ADMIN_PASSWORD=changeme
```

### mem_limit note

`mem_limit` on `prometheus` is enforced by Docker Engine directly. `deploy.resources` is only respected in Swarm mode and is not used here.

### Bring up / verify

```powershell
cd g:\projects\notesystem\dashnotesystemv1
docker compose up -d api prometheus
```

### Validation gate (confirmed)

| Check | URL / command | Expected |
|-------|----------------|----------|
| Prometheus targets | http://localhost:9090/targets | Job **`dashnote_api`**, endpoint `http://api:8000/metrics`, **State: UP** (green) |
| Targets API | `curl.exe -sS http://localhost:9090/api/v1/targets` | `"health":"up"` for `job":"dashnote_api"` |

On the targets page, **State: UP** means the last scrape succeeded (`health: up` in the API). If the API container is down, the target shows **DOWN** with a last error such as connection refused.

### Rules

- Do not change existing Compose services when editing monitoring stack.
- Prometheus scrapes the **`api`** service directly (not nginx on :80).

---

## Step 6 — Grafana dashboards + docs (optional)

**Human guide:** [`docs/observability.md`](../observability.md) (architecture, validation, troubleshooting). Also referenced from [system.md](./system.md), [ai.md](./ai.md), and [lld.md](./lld.md) §4.16.

Grafana dashboards are **optional**. Local Compose does not start Grafana. Provisioning files below are for operators who add Grafana or use Grafana Cloud.

### Provisioning files

| File | Role |
|------|------|
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | Default Prometheus datasource → `http://prometheus:9090` |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | File provider, folder **DashNote** |
| `monitoring/grafana/provisioning/dashboards/api_overview.json` | **API Overview** — 4 panels |

### Dashboard queries (Step 4 metric names only)

| Panel | Expression |
|-------|------------|
| Request Rate | `sum(rate(dashnote_api_http_requests_total[5m]))` |
| Error Rate (5xx) | `sum(rate(dashnote_api_http_requests_total{status=~"5.."}[5m]))` |
| P95 Latency | `histogram_quantile(0.95, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))` |
| P99 Latency | `histogram_quantile(0.99, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))` |

Uses `_bucket` because Step 4 confirmed `dashnote_api_http_request_duration_seconds_bucket` on `/metrics`.

### Reload + validate (only if you run Grafana yourself)

```powershell
# Not part of default docker compose up — add a grafana service first, or use Grafana Cloud
# UI: DashNote folder → API Overview
```

Pinned `prom/prometheus:v2.51.2` is the local Compose metrics image. `grafana/grafana:10.4.2` remains the documented optional UI image; see `docs/observability.md`.

---

## Stack (live)

```
Nginx → FastAPI
          ├─ JSON logs (stdout)
          ├─ Langfuse (RAG/agent traces)
          └─ Prometheus (:9090)  [Grafana optional / Cloud]
```

## Retrieval-depth traces (Tier 1)

When Langfuse keys are set (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`), RAG retrieval spans record **identities + scores**, not counts only:

- Span `retrieval` output includes `retrieved[]` (`chunk_id`, `note_id`, `file_id`, `score`), plus `chunk_ids` / `note_ids` / `scores`
- Empty retrieval attaches score `empty_retrieval=1` on the parent trace (soft; never crashes when Langfuse is off)

### Operator verify (local)

1. Ensure Langfuse env vars are in `.env` and restart API
2. `POST /ai/chat` with a real question that hits notes
3. Open Langfuse UI → latest `rag.answer` trace → `retrieval` span → confirm `retrieved` / scores
4. Ask a nonsense query → confirm `empty_retrieval` score when no chunks return

AI modules must not import the Langfuse SDK — only `observability.tracing` helpers.
