## Why

Hosted chat on aisystem.world feels slow, and Langfuse cannot explain it. The project receives traces, but root rows are unnamed and unclosed, retrieval and context spans never export, time to first token is empty, and every row is `environment=default`, so a laptop run cannot be told apart from the API. Live `GET /health/ai` currently resolves to `nvidia_nim/openai/gpt-oss-20b`, a candidate the docs already treat as a hang risk, because the health probe caches the first model that answers. Fix tracing first so the next hosted chat is measurable, then change the default model list so that slow id is not the sticky winner.

## What Changes

- Close and name `rag.answer` and `agent.turn` so Langfuse latency is on the trace operators actually open.
- Export `retrieval` and `context_building` child spans, not only `llm_generation` / `call_model`.
- Record time to first token on streaming generations when a first token is observed.
- Tag observations with a deployment environment and `service.name=dashnote-api` so hosted traffic is filterable even if another app shares the Langfuse project.
- Report Langfuse enabled/disabled on soft `GET /health/ai` without secrets or a hard deploy gate.
- Change documented defaults so the primary is `gemini/gemini-2.5-flash`, the fallback is a live small NVIDIA NIM id (Lightning class), and `gpt-oss-20b` is not in the default candidate list. Operators may still pin a heavier id explicitly.
- Show both the configured primary and the cached resolved model on `GET /health/ai` so a fallback stick is visible.
- Sequence implementation: tracing and the health signal first, model-default edits after.

Out of scope: moving Postgres, Redis, or Qdrant closer to the EC2 host; notes-list pagination; replacing `/ai/chat` with the agent; committing live keys.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `observability-langfuse`: Hosted RAG and agent traces must be named, closed, include retrieval and context spans, carry environment and service name, and record time to first token. Soft health must say whether Langfuse is enabled.
- `llm-resilience`: Default candidates prefer Gemini Flash, then a small NIM id that is not `gpt-oss-20b`. Health must expose configured versus cached model. Existing gone, timeout, and rate-limit walks stay.

## Impact

- `src/observability/tracing.py`, `src/observability/langfuse_client.py`, `src/config.py`, `src/core/health.py`
- `.env.example` and `.env.production.example` (names and model ids only; no live secrets)
- Tests under `tests/observability/` and `tests/shared/`
- Operator docs for Langfuse filters and the model list (`docs/documentation/observe.md`, `docs/documentation/ai.md` or `docs/nvidia.md` as already used)
- VPS `.env` model lines are an operator step after the code defaults change; this change does not SSH or commit that file
