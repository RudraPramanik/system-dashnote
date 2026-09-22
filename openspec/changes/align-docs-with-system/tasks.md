## 1. Hub — system.md vs mounted API

- [x] 1.1 Diff `src/main.py` `register_routes` against the `system.md` router table; add `ai_routes/feedback.py` / `POST /ai/feedback` (JWT `wid` only; chat/agent do not require it)
- [x] 1.2 Update `system.md` Metrics + Observability: name `dashnote_api_*` and `dashnote_ai_*`; one-paragraph L3 summary (traces, feedback, not a production SLO, not the hard `/health` gate); link `observe.md` and `evals/BLUEPRINT.md` without inlining Langfuse env tables
- [x] 1.3 Add observability/feedback pytest pointers to the Testing section (`tests/ai_routes/test_feedback.py`, `tests/observability/`) if missing

## 2. Eval map status

- [x] 2.1 In `evals/BLUEPRINT.md`, mark L3 as implemented/done (not “this phase” / “current implementation phase”); leave thresholds, generator, and agent answer goldens as later
- [x] 2.2 Confirm `evals/README.md` L3 row already says implemented; edit only if it still contradicts the hub

## 3. Sibling keep-set

- [x] 3.1 Add `POST /ai/feedback` to the `ai.md` router law and a one-line note that turns complete without feedback
- [x] 3.2 Update `lld.md` composition: mounted AI routes include feedback; metrics mention `dashnote_api_*` and `dashnote_ai_*`
- [x] 3.3 Update `openspec/config.yaml` HTTP surface (and product domains if needed) so `/ai` lists `POST /ai/feedback` with JWT `wid` only
- [x] 3.4 If `readme.md` enumerates `/ai` routes or built capabilities, add feedback without claiming A7/TLS or production-grade startup

## 4. Frontend guide

- [x] 4.1 Add an optional `POST /ai/feedback` subsection to `frontendguide.md` (`thread_id` + thumbs or 1–5, optional `trace_id`, no `workspace_id` override)
- [x] 4.2 Leave B-gate checklist unchanged (feedback UI not required)

## 5. Verify (docs-only)

- [x] 5.1 Grep keep-set (`system.md`, `ai.md`, `lld.md`, `frontendguide.md`, `openspec/config.yaml`) for `/ai/feedback`; confirm `src/main.py` still mounts the router
- [x] 5.2 Grep `evals/BLUEPRINT.md` so L3 is not labeled an open implementation phase; confirm `system.md` still says HTTP-IP ≠ HTTPS/A7
- [x] 5.3 Confirm no files were deleted and `docs/observability.md` links remain (leave `consolidate-docs` retire-set untouched)
