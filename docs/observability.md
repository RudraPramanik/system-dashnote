# DashNote Observability

Production-oriented guide for logging, LLM tracing (Langfuse), and metrics (Prometheus; Grafana optional) in local Docker Compose.

**Agent quick reference:** [docs/documentation/observe.md](./documentation/observe.md)  
**Implementation blueprint:** [docs/documentation/blueprint/observation-blueprint.md](./documentation/blueprint/observation-blueprint.md)

---

## Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │ HTTP :80 / :8000
                    ┌──────▼──────┐
                    │    Nginx    │  (optional path :80)
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │   FastAPI (api:8000)    │
              │  src/main.py lifespan   │
              └─┬──────────┬──────────┬─┘
                │          │          │
     JSON logs  │          │          │  GET /metrics
     (stdout)   │          │          │
                │          │          ▼
                │          │   ┌──────────────┐
                │          │   │  Prometheus  │  :9090, 7d retention
                │          │   │  scrape 15s  │
                │          │   └──────┬───────┘
                │          │          │
                │          │          ▼
                │          │   [Grafana optional / Cloud — not in default Compose]
                │          │
                │          ▼
                │   ┌──────────────┐
                └──►│   Langfuse   │  cloud (HTTPS)
                    │  rag.answer  │
                    │  + spans     │
                    └──────────────┘
```

**Not in scope:** Loki, Tempo, Jaeger, OpenTelemetry Collector.

### Container images (lightweight choices)

| Service | Image | Notes |
|---------|--------|--------|
| Prometheus | `prom/prometheus:v2.51.2` | Official minimal binary image; no smaller drop-in with full PromQL compatibility. |
| Grafana (optional) | `grafana/grafana:10.4.2` | Not in default `docker-compose.yml`; use Grafana Cloud or add a service manually. |

Alternatives (VictoriaMetrics single-binary, etc.) would change scrape/query semantics and are not used here. Local Compose ships Prometheus; Grafana UI is optional.

---

## 1. JSON logging

### How it works

- `setup_logging()` runs once at the start of the FastAPI lifespan in `src/main.py`.
- Log lines are JSON: `timestamp`, `level`, `logger`, `message`, plus optional `extra` fields.

### Validate

```powershell
cd g:\projects\dashnotesystemv1
docker compose logs --tail 20 api
```

Each line should parse as JSON (starts with `{`).

### Troubleshooting: JSON format missing

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| Plain-text or duplicate lines | `logging.basicConfig()` or third-party handler elsewhere | Only call `setup_logging()` in lifespan; remove other root handlers |
| No structured `extra` | Logger called without `extra={}` | Expected for simple messages; use `get_logger(__name__).info(..., extra={...})` for context |

---

## 2. Langfuse (LLM / RAG traces)

### Required environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `LANGFUSE_PUBLIC_KEY` | Yes (with secret) | `""` | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | Yes (with public) | `""` | `sk-lf-...` |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | EU cloud; US: `https://us.cloud.langfuse.com` |

Tracing is **enabled** when both keys are non-empty (`settings.langfuse_enabled`).

Set keys in `.env` (never commit). Rebuild/restart API after changes.

### Code paths

| File | Role |
|------|------|
| `src/observability/langfuse_client.py` | Lazy `get_langfuse_client()` |
| `src/observability/tracing.py` | `rag_trace`, `rag_span` |
| `src/ai/services/rag_service.py` | `answer()` / `stream_answer()` only |

**Rules:** Do not call `get_langfuse_client()` from `main.py` lifespan. `RagService` must not import the Langfuse SDK directly.

### Healthy trace (what “good” looks like)

After a successful `/ai/chat` or `/ai/chat/stream` with valid JWT and keys:

1. Root observation **`rag.answer`** in Langfuse UI.
2. Child spans: **`retrieval`** → **`context_building`** → **`llm_generation`**.
3. Each span output includes **`latency_ms`**.
4. **`retrieval`**: `chunks_retrieved`.
5. **`context_building`**: `chunks_used`, `char_budget`.
6. **`llm_generation`**: token fields when LiteLLM provides usage; **`cost`** when available.
7. Metadata includes **`workspace_id`**, **`user_id`**, **`role`** (no raw JWT).

### Validate

```powershell
# Module import (no HTTP)
$env:PYTHONPATH = "src"
python -c "from observability import rag_trace, rag_span; print('PASS')"

# Trigger trace (replace <TOKEN>)
curl.exe -sS -X POST http://127.0.0.1/ai/chat `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"What is in my notes?\"}"
```

Check Langfuse → Traces for `rag.answer`.

### Troubleshooting: Langfuse client returns `None`

| Symptom | Cause | Fix |
|---------|--------|-----|
| WARNING: `Langfuse disabled: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not both set` | Missing keys | Set both in `.env`, restart `api` |
| WARNING: `Langfuse client init failed` | Bad keys, wrong host, network | Verify keys in Langfuse UI; check `LANGFUSE_HOST`; outbound HTTPS from container |
| No traces but client OK | No RAG traffic or keys only on host not in container | Ensure `env_file: .env` on `api`; call `/ai/chat` with JWT |

App continues running when Langfuse is disabled (no-op tracing).

---

## 3. Prometheus

### Scrape configuration

**File:** `monitoring/prometheus.yml`

| Setting | Value |
|---------|--------|
| Scrape interval | 15s |
| Job | `dashnote_api` |
| Target | `api:8000` |
| Metrics path | `/metrics` |

**Compose:** `prometheus` service, port **9090**, TSDB retention **7d** (`--storage.tsdb.retention.time=7d`), `mem_limit: 256m`.

### Exact HTTP metric names (Step 4 — use only these in dashboards)

| Role | Metric | Type |
|------|--------|------|
| Request total | `dashnote_api_http_requests_total` | counter |
| Latency histogram | `dashnote_api_http_request_duration_seconds` | histogram |
| Latency buckets (for percentiles) | `dashnote_api_http_request_duration_seconds_bucket` | histogram bucket |
| High-res histogram | `dashnote_api_http_request_duration_highr_seconds` | histogram |

Labels on counter/handler histogram: `handler`, `method`, `status`.

Process metrics (`python_*`, `process_*`) have no `dashnote_api_` prefix — expected.

### Validate

```powershell
docker compose up -d api prometheus

curl.exe -sS http://localhost:8000/health
curl.exe -sS http://localhost:8000/metrics | findstr dashnote_api

# Target health
curl.exe -sS http://localhost:9090/api/v1/targets
```

**Targets UI:** http://localhost:9090/targets — job `dashnote_api`, **State: UP**.

### Troubleshooting: target DOWN

| Symptom | Cause | Fix |
|---------|--------|-----|
| `connection refused` on `api:8000` | API container not running | `docker compose up -d api` |
| Target UP, no app metrics | No traffic yet | `curl http://localhost:8000/health` |
| Scrape 404 | Wrong path | Must be `/metrics` on API (not nginx :80) |

---

## 4. Grafana (optional)

**Not part of default local Compose.** Prefer Grafana Cloud remote_write (prod observability profile). Provisioning files under `monitoring/grafana/` remain for operators who add a Grafana container.

### Access (only if you run Grafana yourself)

| Item | Value |
|------|--------|
| URL | http://localhost:3001 (only when a Grafana service is added) |
| User | `admin` |
| Password | `GRAFANA_ADMIN_PASSWORD` in `.env` |

### Provisioning layout

```
monitoring/grafana/provisioning/
├── datasources/prometheus.yml   # Prometheus @ http://prometheus:9090
└── dashboards/
    ├── dashboard.yml            # folder: DashNote
    └── api_overview.json        # API Overview dashboard
```

### Dashboard: API Overview

**Folder:** DashNote  
**Title:** API Overview  
**UID:** `dashnote-api-overview`

| Panel | PromQL |
|-------|--------|
| Request Rate | `sum(rate(dashnote_api_http_requests_total[5m]))` |
| Error Rate (5xx) | `sum(rate(dashnote_api_http_requests_total{status=~"5.."}[5m]))` |
| P95 Latency | `histogram_quantile(0.95, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))` |
| P99 Latency | `histogram_quantile(0.99, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))` |

Histogram panels use `_bucket` because Step 4 confirmed `dashnote_api_http_request_duration_seconds_bucket` on `/metrics`.

### Validate without Grafana

```powershell
docker compose up -d api prometheus
curl.exe -sS http://localhost:9090/targets
```

### Troubleshooting: empty dashboard panels (if Grafana is running)

| Symptom | Cause | Fix |
|---------|--------|-----|
| All panels empty | No requests since scrape started | Hit `/health` or real routes several times; wait 15–30s |
| Wrong metric names | Dashboard not using Step 4 names | Use exact names above; reload Grafana |
| Datasource error | Prometheus down | `docker compose ps prometheus`; check http://localhost:9090/targets |
| P95/P99 flat or no data | No histogram observations yet | Generate API traffic; confirm `_bucket` in `/metrics` |

## Full stack validation (checklist)

```powershell
cd g:\projects\notesystem\dashnotesystemv1
docker compose up -d api prometheus
```

| Layer | Command / URL | Pass criteria |
|-------|----------------|---------------|
| Logs | `docker compose logs --tail 5 api` | JSON lines |
| Metrics | `curl http://localhost:8000/metrics` | `dashnote_api_http_requests_total` present |
| Prometheus | http://localhost:9090/targets | `dashnote_api` UP |
| Grafana | optional / Cloud | Not required for local Compose pass |
| Langfuse | `/ai/chat` + UI | `rag.answer` trace (when keys set) |

---

## File index

| Path | Purpose |
|------|---------|
| `src/observability/logging.py` | JSON logging |
| `src/observability/langfuse_client.py` | Langfuse client |
| `src/observability/tracing.py` | RAG spans |
| `src/main.py` | `setup_logging()`, Prometheus instrumentator |
| `monitoring/prometheus.yml` | Scrape config |
| `monitoring/grafana/provisioning/` | Grafana datasource + dashboards |
| `docker-compose.yml` | `api`, `prometheus` services (Grafana not default) |
| `.env.example` | `GRAFANA_ADMIN_PASSWORD`, Langfuse vars |
