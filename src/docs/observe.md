# DashNote Observability

Implementation and operations guide for platform observability. Canonical location for this documentation is **`src/docs/observe.md`**.

## Status

| Step | Feature | Status |
|------|---------|--------|
| 1 | Structured JSON logging | **Done** |
| 2 | Langfuse client (lazy) | Planned |
| 3 | RAG tracing (`RagService`) | Planned |
| 4 | Prometheus `/metrics` | Planned |
| 5 | Docker Prometheus + Grafana | Planned |
| 6 | Grafana dashboards + runbooks | Planned |

---

## Step 1 — Structured JSON logging

### Architecture

```
API process (uvicorn → src.main:app)
    │
    ├─ lifespan startup: setup_logging()  ← only call site
    │
    └─ root logger + JsonFormatter (stdout)
           ↑ propagate
           uvicorn / uvicorn.error / uvicorn.access
```

All application modules may keep using `logging.getLogger(__name__)` today; new code should prefer `from observability import get_logger`. Both receive the same JSON formatter after `setup_logging()` runs.

### Files

| Path | Role |
|------|------|
| `src/observability/logging.py` | `JsonFormatter`, `setup_logging()`, `get_logger()` |
| `src/observability/__init__.py` | Public exports |
| `src/main.py` | Calls `setup_logging()` as the **first** line of `lifespan` |

### Import law (`logging.py`)

- **Allowed:** `logging`, `json`, `datetime`, `sys` (stdlib only)
- **Forbidden:** FastAPI, SQLAlchemy, `config`, domain modules

### JSON log schema

Each line is one JSON object:

| Field | Required | Source |
|-------|----------|--------|
| `timestamp` | Yes | UTC ISO 8601 |
| `level` | Yes | Log level name |
| `logger` | Yes | Logger name (e.g. `ai.services.rag_service`) |
| `message` | Yes | Log message |
| `request_id` | No | `extra={"request_id": "..."}` |
| `workspace_id` | No | `extra={"workspace_id": "..."}` |
| `user_id` | No | `extra={"user_id": "..."}` |
| `route` | No | `extra={"route": "..."}` |
| `latency_ms` | No | `extra={"latency_ms": 123}` |
| `exception` | No | Present when `exc_info=True` |

Example:

```json
{"timestamp": "2026-06-03T12:00:00.123456+00:00", "level": "INFO", "logger": "main", "message": "LangGraph checkpointer ready"}
```

With context:

```python
from observability import get_logger

logger = get_logger(__name__)
logger.info(
    "rag_service.answer complete",
    extra={
        "workspace_id": workspace_id,
        "latency_ms": 842.5,
    },
)
```

### Behaviour

- **Idempotent:** `setup_logging()` is a no-op after the first successful (or fallback) configuration.
- **Never raises:** On failure, falls back to `logging.basicConfig` with a plain text format so the API still starts.
- **Uvicorn:** Clears handlers on `uvicorn`, `uvicorn.error`, and `uvicorn.access` and sets `propagate=True` so access and server logs use the same JSON formatter as the app.
- **Worker:** ARQ worker (`src/worker/main.py`) keeps its own text formatter until a later step; API and worker log formats may differ in Compose.

### Wiring rule

`setup_logging()` must **only** be invoked from `src/main.py` inside the FastAPI `lifespan` context manager, as the first statement before ARQ, Qdrant, or checkpointer init.

---

## Validation — Step 1

### Docker (recommended)

From the repository root:

```powershell
docker compose up -d --build api
docker compose logs --tail 30 api
```

Expect lines that parse as JSON with keys `timestamp`, `level`, `logger`, `message`. Startup should include a JSON line for checkpointer readiness or degradation from logger `main`.

Trigger traffic and confirm access logs are JSON:

```powershell
curl.exe -sS http://127.0.0.1/health
docker compose logs --tail 10 api
```

### Local uvicorn (optional)

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH = "src"
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
curl.exe -sS http://127.0.0.1:8000/health
```

Stdout from the API process should show JSON lines after lifespan runs.

### Quick JSON parse check (PowerShell)

```powershell
docker compose logs --tail 5 api | ForEach-Object {
  if ($_ -match '^\{') { $_ | ConvertFrom-Json | Format-List timestamp, level, logger, message }
}
```

If `ConvertFrom-Json` succeeds, the formatter is active.

---

## Troubleshooting — logging

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| Plain text logs, not JSON | Lifespan not run yet, or logs from before `setup_logging()` | Hit `/health` or wait for startup; check lines after "Application startup complete" |
| Mixed formats | Worker container vs API container | Inspect `api` service only for Step 1 gate |
| `setup_logging` not applied | Import error before lifespan | Check `docker compose logs api` for tracebacks on boot |
| Missing `workspace_id` in JSON | Caller did not pass `extra=` | Expected until routes/middleware attach context (future step) |

---

## Planned stack (Steps 2–6)

```
Client → Nginx → FastAPI (JSON logs, /metrics)
                    │
                    ├─ Langfuse (LLM/RAG traces)
                    └─ Prometheus → Grafana
```

Details will be appended to this document as each step lands. Blueprint reference: `src/docs/blueprint/observation-blueprint.md`.
