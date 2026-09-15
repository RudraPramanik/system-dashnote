## 1. Tracing facade (no product behavior change)

- [ ] 1.1 Extend `observability.tracing` with generic parent/child context managers and a contextvar parent; keep `rag_trace` / `rag_span` / `score_trace` as aliases
- [ ] 1.2 Export new helpers from `observability/__init__.py`; Langfuse SDK remains only in `langfuse_client.py` and `tracing.py`
- [ ] 1.3 Unit-test no-op when keys missing; unit-test nested `start_trace` becomes a child of the active parent (`tests/observability/`)

## 2. Quality counters

- [ ] 2.1 Add low-cardinality Prometheus counters `dashnote_ai_empty_retrieval_total`, `dashnote_ai_agent_interrupt_total`, `dashnote_ai_llm_fallback_total` (no user/question labels)
- [ ] 2.2 Increment empty-retrieval from the existing RAG empty path (alongside `empty_retrieval` score); increment fallback from the shared LLM fallback path
- [ ] 2.3 Confirm `GET /metrics` still includes `dashnote_api_http_requests_total` (`tests/observability/` or existing metrics test)

## 3. Agent turn traces (contracts unchanged)

- [ ] 3.1 Wrap `/ai/agent`, `/ai/agent/stream`, `/ai/agent/resume`, `/ai/agent/reject` with `agent.turn` parent (JWT `workspace_id` / `user_id` / `role` only)
- [ ] 3.2 Open a generation span around `call_model` in `workspace_assistant.py` via the facade (no Langfuse SDK import)
- [ ] 3.3 Span mutation tools / HITL interrupt; increment `dashnote_ai_agent_interrupt_total` on `approval_required`
- [ ] 3.4 Verify nested `rag.answer` when search/summarize tools run under an active agent parent (unit with fake client)
- [ ] 3.5 Add optional `trace_id` on chat/agent JSON (and stream `done` if present); required fields and HITL payloads stay as today
- [ ] 3.6 Run existing HITL / agent tests; they MUST still pass (`tests/` agent-hitl suite)

## 4. User feedback API

- [ ] 4.1 Add `POST /ai/feedback` (JWT, `thread_id`, thumbs or 1–5, optional `trace_id`); authorize thread by JWT `wid` only
- [ ] 4.2 Attach Langfuse user-feedback score when enabled; 2xx with tracing-unavailable when Langfuse is off (no 5xx)
- [ ] 4.3 Tests: foreign-workspace thread is 403/404; chat/agent still work without ever calling feedback (`tests/ai_routes/` or equivalent)

## 5. Operator judge path (not CI)

- [ ] 5.1 Document Langfuse dataset seed (from goldens or failing traces) + sampled faithfulness judge in `evals/README.md`; state it is operator/nightly only
- [ ] 5.2 Add a non-CI operator script or Langfuse UI steps under `evals/` that MUST NOT be invoked from `.github/workflows/ci.yml`
- [ ] 5.3 Add EXPERIMENTS loop citing judge/trace or `PASS: X/Y`, with environment label (not a production SLO)
- [ ] 5.4 Update `docs/documentation/observe.md` (and interview evidence if needed) with the three planes: Prometheus health, Langfuse traces/judges, fixture CI

## 6. Compatibility gate

- [ ] 6.1 `python evals/run_eval.py --mode fixture` still prints `PASS: 20/20` (or current honest X/Y if goldens unchanged)
- [ ] 6.2 Confirm `.github/workflows/ci.yml` fixture eval step has no Langfuse/judge dependency
- [ ] 6.3 Smoke: `/ai/chat` and `/ai/agent` request/response meaning unchanged (required fields present); `/health` still hard-gates DB+Redis
