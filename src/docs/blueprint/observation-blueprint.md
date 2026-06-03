STEP 0 — Architecture Discovery (new)
Act as a senior platform engineer doing a pre-implementation audit.

Before any observability changes are made, analyze the existing codebase.

Do NOT modify any file in this step.

Produce a written report covering:

1. FastAPI entrypoint:
   - file path of main.py
   - how the app object is created
   - whether a lifespan context manager exists
   - how routers are registered

2. Settings/config:
   - file path of the config/settings module
   - how Settings is instantiated (singleton, Depends, direct import)
   - whether there is an existing .env.example

3. RagService:
   - exact file path
   - signature of answer() and stream_answer()
   - what gets imported at the top of that file
   - whether Langfuse, LangSmith, or any observability is already present

4. LiteLLM integration point:
   - where litellm.acompletion is called
   - whether usage data is available on the response object

5. Startup/lifespan:
   - is there an existing @asynccontextmanager lifespan?
   - what currently runs at startup?

6. Docker:
   - docker-compose.yml location
   - existing services
   - whether a monitoring/ directory exists

7. Potential conflicts:
   - any existing logging configuration that would clash
   - any existing observability imports
   - any import law violations that would affect placement of new code

8. Final output must include:
   Files to be created (path + purpose)
   Files to be modified (path + what changes)
   Assumptions you are making
   Any risks or open questions

Wait for explicit approval before making any changes.

STEP 1 — Structured Logging Foundation
Act as a senior backend platform engineer.

Introduce production-grade structured logging into DashNoteSystem.
Do NOT change any business logic.

Requirements:

1. Create these files:
   src/observability/__init__.py    — exports: get_logger, setup_logging
   src/observability/logging.py     — implementation

2. Implement setup_logging():
   - Configures root logger with a JSON formatter
   - Replaces uvicorn's default handlers so log format stays consistent
   - Idempotent: safe to call more than once
   - Never raises: wrap setup in try/except, fall back to basicConfig

3. Implement get_logger(name: str) -> logging.Logger:
   - Single import point for all log calls across the codebase
   - Callers pass extra={} for optional context fields

4. JSON format per entry:
   Required:  timestamp (ISO 8601), level, logger, message
   Optional via extra={}: request_id, workspace_id, user_id, route, latency_ms

5. Wire setup_logging() in main.py:
   - Call it as the FIRST thing inside the lifespan context manager
   - If no lifespan exists yet, add one
   - Do not call setup_logging() from anywhere else

6. Do NOT modify any repository, service, AI module, or router.

7. Import law for observability package:
   - logging.py imports: stdlib only (logging, json, datetime)
   - No FastAPI, SQLAlchemy, config, or domain imports in logging.py

8. Show every file you plan to modify before applying any change.

After implementation provide:
- List of created files
- List of modified files
- Exact command to verify JSON log output
Validation gate: docker compose up -d && docker compose logs -f api shows valid JSON entries. Do not proceed until confirmed.

STEP 2 — Langfuse Foundation (lazy client, no traces yet)
Act as a senior backend observability engineer.

Add Langfuse client infrastructure only. No tracing code yet.

Requirements:

1. Add to config.py Settings:

   LANGFUSE_PUBLIC_KEY: str = ""
   LANGFUSE_SECRET_KEY: str = ""
   LANGFUSE_HOST: str = "https://cloud.langfuse.com"

   Add a computed property:
   @property
   def langfuse_enabled(self) -> bool:
       return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

2. Create src/observability/langfuse_client.py:

   - Module-level variables only:
     _client = None
     _initialized = False

   - Implement get_langfuse_client() -> Optional[Langfuse]:
     * If _initialized is True, return _client immediately (no re-init)
     * If langfuse_enabled is False: log warning, set _initialized=True,
       return None
     * On init failure: log warning, set _initialized=True, return None,
       never raise
     * On success: store in _client, set _initialized=True, return client

   No asyncio.Lock. No startup wiring. Purely lazy.

3. Export get_langfuse_client from src/observability/__init__.py.

4. Do NOT call get_langfuse_client() from main.py or any lifespan hook.
   It initializes on first actual use inside the tracing layer (Step 3).

5. Do NOT import Langfuse in any router, repository, or service.

6. Import law for langfuse_client.py:
   Allowed: stdlib, config, langfuse SDK
   Forbidden: FastAPI, SQLAlchemy, any domain module

7. Update .env.example with:
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=
   LANGFUSE_HOST=https://cloud.langfuse.com

8. Show files before modifying.

After implementation provide:
- How to verify the module loads without errors
- What log line appears when keys are missing
- What log line appears when keys are present and init succeeds
Validation gate: app starts cleanly in both cases (keys present and missing). Do not proceed until both verified.

STEP 3 — RAG Observability
Act as a principal AI platform engineer.

Instrument RagService with Langfuse traces.

This step has two parts: first build the reusable tracing abstraction,
then wire it into RagService. Future services (agent, memory, workflow)
will consume the same abstraction without any changes to tracing.py.

PART A — Create src/observability/tracing.py

Implement two context managers:

1. rag_trace(name: str, metadata: dict) -> AsyncContextManager
   - Calls get_langfuse_client()
   - If client is None: yields a no-op object with .span() and .update()
   - If client is available: creates a Langfuse trace, yields it
   - Flushes in finally block
   - Never raises

2. rag_span(parent, name: str, input_data: dict) -> AsyncContextManager
   - If parent is a no-op: yields a no-op
   - Otherwise creates a child span on the parent trace
   - Records latency automatically using time.monotonic()
   - Never raises

The no-op objects must have the same interface as real Langfuse objects
so callers never need to check for None.

Export both from src/observability/__init__.py.

PART B — Modify src/ai/services/rag_service.py

Wire tracing into answer() and stream_answer() only.
Do not change any method signatures or return types.

In answer():
  async with rag_trace("rag.answer", {workspace_id, user_id, role}) as trace:
    async with rag_span(trace, "retrieval", {question}) as span:
      # existing retrieval code
      span.update(output={chunks_retrieved: N})
    async with rag_span(trace, "context_building", {}) as span:
      # existing context build code
      span.update(output={chunks_used: N, char_budget: N})
    async with rag_span(trace, "llm_generation", {model}) as span:
      # existing litellm call
      # if usage data available on response: span.update(output={tokens, cost})

In stream_answer():
  Same trace structure.
  llm_generation span wraps the full stream loop.
  Flush in finally.

Import law for rag_service.py after this change:
  May import: src/observability/tracing.py
  Must NOT import: langfuse SDK directly
  Must NOT import: FastAPI, RequestContext

IMPORTANT: Do not touch any router, repository, or other service.
Show the full planned diff for rag_service.py before applying.

After implementation provide:
- curl command to trigger POST /ai/chat
- curl command to trigger POST /ai/chat/stream
- Exact items to verify in Langfuse UI:
    trace named rag.answer visible
    3 child spans: retrieval, context_building, llm_generation
    latency_ms on each span
    chunks_retrieved and chunks_used recorded
    LLM token usage visible (if returned by litellm response)
Validation gate: both endpoints traced, all 3 spans visible with data, token usage populated. Do not proceed until all items confirmed.

STEP 4 — Prometheus Metrics
Act as a backend platform engineer.

Add lightweight HTTP-level Prometheus metrics to DashNoteSystem.

Requirements:

1. Add to requirements.txt (or pyproject.toml, whichever exists):
   prometheus-fastapi-instrumentator>=0.11.0

2. Modify src/main.py only:
   - Import: from prometheus_fastapi_instrumentator import Instrumentator
   - After app creation and after all routers are registered, add:

     Instrumentator(
         metric_namespace="dashnote",
         metric_subsystem="api",
         should_group_status_codes=False,
         should_ignore_untemplated=True,
     ).instrument(app).expose(app, endpoint="/metrics")

   Placement rule: attach after app creation, before the application
   starts serving (i.e., not inside a request handler).

3. After adding the instrumentation, run:

     docker compose up -d --build api
     curl http://localhost:8000/metrics

   Capture the EXACT metric names that appear in the output.
   Specifically look for:
   - the histogram metric name (needed for dashboard queries in Step 6)
   - the counter metric name for request totals

   Include these exact names in your implementation report.

4. Do NOT modify any router, repository, service, or observability module.
5. Do NOT add custom metrics in this step.
6. Show the diff for main.py before applying.

After implementation provide:
- Exact metric names observed in /metrics output
- Confirm dashnote_api prefix is present on all metrics
Validation gate: curl http://localhost:8000/metrics | grep dashnote_api returns metrics with the correct prefix. Record exact histogram name for Step 6. Do not proceed until confirmed.

STEP 5 — Docker Infrastructure
Act as a DevOps and platform engineer.

Add Prometheus and Grafana to the existing docker-compose.yml.

Requirements:

1. Create monitoring/prometheus.yml:

   global:
     scrape_interval: 15s
     evaluation_interval: 15s
   scrape_configs:
     - job_name: dashnote_api
       static_configs:
         - targets: ['api:8000']
       metrics_path: /metrics

2. Add to docker-compose.yml (do NOT touch existing services):

   prometheus:
     image: prom/prometheus:v2.51.2
     volumes:
       - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
       - prometheus_data:/prometheus
     command:
       - '--config.file=/etc/prometheus/prometheus.yml'
       - '--storage.tsdb.retention.time=7d'
     ports:
       - "9090:9090"
     mem_limit: 256m
     restart: unless-stopped

   grafana:
     image: grafana/grafana:10.4.2
     ports:
       - "3001:3000"
     environment:
       GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-changeme}
       GF_USERS_ALLOW_SIGN_UP: "false"
       GF_AUTH_ANONYMOUS_ENABLED: "false"
     volumes:
       - grafana_data:/var/lib/grafana
       - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
     depends_on:
       - prometheus
     mem_limit: 512m
     restart: unless-stopped

3. Add to the volumes section at the bottom:
   prometheus_data:
   grafana_data:

4. Add GRAFANA_ADMIN_PASSWORD to .env.example.

5. Add a comment in docker-compose.yml above prometheus and grafana:
   # mem_limit is enforced by Docker Engine directly.
   # deploy.resources is only respected in Swarm mode and is not used here.

6. Show complete diff of docker-compose.yml before applying.
   Show monitoring/prometheus.yml content before creating it.

After implementation provide:
- docker compose up -d command to verify
- Prometheus targets page URL and what "State: UP" looks like
- Grafana login URL
Validation gate: http://localhost:3001 loads Grafana, http://localhost:9090/targets shows dashnote_api as State: UP. Do not proceed until both confirmed.

STEP 6 — Dashboards + Documentation
Act as a production observability engineer.

Create Grafana provisioning and final documentation.

IMPORTANT BEFORE WRITING ANY DASHBOARD JSON:
The exact metric names to use were captured in Step 4.
Use those exact names. Do not assume or invent metric names.
If the histogram metric from Step 4 does not have _bucket suffix,
do not use histogram_quantile() — use a simpler rate() query instead.

Requirements:

1. Create monitoring/grafana/provisioning/datasources/prometheus.yml:

   apiVersion: 1
   datasources:
     - name: Prometheus
       type: prometheus
       url: http://prometheus:9090
       isDefault: true
       editable: false

2. Create monitoring/grafana/provisioning/dashboards/dashboard.yml:

   apiVersion: 1
   providers:
     - name: DashNote
       folder: DashNote
       type: file
       options:
         path: /etc/grafana/provisioning/dashboards

3. Create monitoring/grafana/provisioning/dashboards/api_overview.json

   4 panels using the EXACT metric names from Step 4:

   Panel 1 — Request Rate
   expr: rate(<exact_requests_total_metric>[5m])

   Panel 2 — Error Rate
   expr: rate(<exact_requests_total_metric>{status=~"5.."}[5m])

   Panel 3 — P95 Latency (only if histogram buckets confirmed in Step 4)
   expr: histogram_quantile(0.95, rate(<exact_histogram_bucket_metric>[5m]))

   Panel 4 — P99 Latency (only if histogram buckets confirmed in Step 4)
   expr: histogram_quantile(0.99, rate(<exact_histogram_bucket_metric>[5m]))

   If histogram buckets are NOT present, replace panels 3 and 4 with:
   avg(<exact_duration_metric>) and max(<exact_duration_metric>)

4. Create docs/observability.md covering:
   - Architecture diagram (ASCII) of the full observability stack
   - Langfuse: required env vars, what a healthy trace looks like,
     validation checklist from Step 3
   - Prometheus: scrape config location, metric names, retention setting
   - Grafana: URL, login credentials (reference env var), dashboard location
   - Validation commands for each layer
   - Troubleshooting section:
       Langfuse client returns None (missing keys, network issue)
       Prometheus shows target as DOWN
       Dashboard panels are empty (wrong metric names, no data yet)
       JSON log format not appearing (conflicting logging config)

5. Do NOT add Loki, Tempo, Jaeger, or OpenTelemetry Collector.

After implementation:
- Reload Grafana (docker compose restart grafana)
- Confirm dashboard auto-loads under DashNote folder
- Hit API a few times, confirm panels show data
- Commit docs/observability.md
Validation gate: dashboard loads automatically, all panels show data after hitting the API. docs/observability.md present and complete.