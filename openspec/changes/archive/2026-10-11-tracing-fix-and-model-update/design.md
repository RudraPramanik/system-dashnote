## Context

See proposal.md for why. Tracing today goes through `observability.tracing` only (`start_trace` / `rag_span`). The Langfuse Python client is SDK 3 (`langfuse >= 2.60,<4`, live traces reported `3.15.0`). A root `start_observation` creates a trace wrapper whose name and end time often stay empty, while `retrieval` and `context_building` never show up as observations. Generations that set `as_type="generation"` do land. The client is constructed with keys and host only, so every row is `environment=default` and `service.name=unknown_service`. `GET /health/ai` reports whatever `resolve_llm_model` cached, which on the hosted API is currently `nvidia_nim/openai/gpt-oss-20b`.

## Goals / Non-Goals

**Goals:**

- Make one hosted chat turn visible in Langfuse as a closed `rag.answer` (or `agent.turn`) with `retrieval`, `context_building`, and the generation span, plus time to first token on streams.
- Label those rows so production can be filtered without a second Langfuse project.
- After tracing is in place, switch code and example defaults to Gemini Flash with a Lightning NIM fallback, and show configured versus cached model on soft health.

**Non-Goals:**

- Collocating Postgres, Redis, or Qdrant with the EC2 host.
- Changing the L2 / quality-lab judge model (`gpt-oss-20b` may stay the judge).
- Editing gitignored filled env files or printing live keys.
- Merging `/ai/chat*` and `/ai/agent*`.

## Decisions

### 1. Name and end the trace wrapper, and type every child span

SDK 3 keeps a trace object separate from the span we end. On root start, call `update_trace(name=...)` with the same name (`rag.answer` or `agent.turn`) and the existing metadata. On exit, `end()` that root observation and then `flush()` as today. Child helpers MUST pass `as_type="span"` for `retrieval` and `context_building` (generations keep `as_type="generation"`). `end()` MUST still run if `update(output=...)` fails, so a bad payload cannot drop the span.

Alternative considered: a second Langfuse project and a from-scratch OTEL setup. Rejected for this change; the export bug is in our wrapper, and an environment label is enough to filter the other app that already shares the project.

### 2. Environment and service name at client init

Add an optional setting `LANGFUSE_TRACING_ENVIRONMENT`. Effective value: that setting when non-blank, otherwise `production` when `DEBUG` is false and `development` when `DEBUG` is true. Pass it as `environment=` on the Langfuse client (and set `LANGFUSE_TRACING_ENVIRONMENT` in the process before init if the SDK only reads the env var). Set `OTEL_SERVICE_NAME=dashnote-api` before the client is constructed only when that variable is unset, so Langfuse resource attributes stop saying `unknown_service`. Do not log keys.

Alternative considered: stuffing environment only into span metadata. Rejected because the observations list filters on the SDK environment field, which stayed `default` while metadata was already present.

### 3. Time to first token stays inside the span handle

Add a method on the observability span handle, called from the existing stream loops in RAG and the agent the first time a token is yielded. The handle records that instant and, on finalize, sets the generation `completion_start_time` (Langfuse time-to-first-token). `src/ai/*` still MUST NOT import the Langfuse SDK. Non-streaming completions leave the field unset.

### 4. Soft health shape

`GET /health/ai` gains:

- `langfuse`: `{ "enabled": bool, "host": "<effective host or empty>" }` with no key material. Enabled means both keys are non-empty. This does not affect `status` and does not affect `GET /health`.
- On `llm`: keep `model` as the resolved/cached id (current field). Add `configured_model` from settings and `cached_model` (null when nothing is cached yet).

### 5. Model defaults, after tracing

In `config.py`, `.env.example`, and `.env.production.example` only:

- `LLM_MODEL=gemini/gemini-2.5-flash`
- `LLM_MODEL_FALLBACKS=nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b`

Remove `gpt-oss-20b` from those defaults. Do not change a filled `.env` / VPS file in git. Document that an operator who wants the new list on the host must set the same two lines and recreate `api` and `worker` so the in-process cache drops. Explicit operator overrides, including 120B or `gpt-oss-20b`, still win. Fallback walks for 410, timeout, and 429 stay as they are.

### 6. Implementation order

Ship and verify tracing (including the health Langfuse flag) before editing model defaults. A model change without a closed trace repeats the current blind spot.

## Risks / Trade-offs

- [Gemini 429 on the free tier] → Lightning remains the fallback; rate-limit walk already refuses to stick the 429 id.
- [Lightning itself is slow or flaky] → It is the fallback, not the primary. Wall-clock abort still applies.
- [`OTEL_SERVICE_NAME` affects another exporter in-process] → Set it only when unset; this API process has no other service name today.
- [Shared Langfuse project still mixes the planner app] → Filter `environment=production` and service `dashnote-api`. Moving that other app is an operator choice, not this change.
- [VPS env still pins `gpt-oss-20b` or omits `LLM_MODEL` until recreate] → Migration step below; code defaults alone do not clear a running container's cache or an explicit env override.
- [Child spans still missing after `as_type=span`] → Tests assert the wrapper calls `start_observation` / `end` for retrieval and context. If a live trace still lacks them, the follow-up is the SDK call shape, not a new product behavior.

## Migration Plan

1. Deploy the tracing change. Recreate the API container if Langfuse env vars were added only on the laptop copy of `.env`.
2. Send one chat on the hosted app. Confirm Langfuse shows a closed `rag.answer` with `retrieval`, `context_building`, `llm_generation`, environment `production`, and a time to first token.
3. Then deploy the model-default change. On the VPS `.env`, set the two model lines to match the example (no other secrets in git) and recreate `api` and `worker`.
4. Confirm `GET /health/ai` shows `configured_model` Gemini Flash. If `cached_model` is still `gpt-oss-20b`, the container was not recreated or the VPS env still overrides the default.
5. Rollback: restore the previous `LLM_MODEL` / `LLM_MODEL_FALLBACKS` on the VPS and recreate the containers. Tracing changes can stay; they are soft-fail.

## Open Questions

None that change the specs or the task order. If NVIDIA retires the Lightning id, the operator replaces the fallback string the same way other NIM retirements are handled.
