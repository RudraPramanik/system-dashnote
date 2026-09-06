## 1. Docs window + LangGraph inventory

- [ ] 1.1 Update `goal.md` / `blueprint8.md` (and ship-plan pointer if needed) to record the active **local AI-depth-first Tier 1** window: deepeners allowed on Compose; forbid production-live / hire-ready claims until A4/A7
- [ ] 1.2 Inventory installed LangGraph version + interrupt/resume APIs against current `workspace_assistant.py` / checkpointer; record chosen API and tighten `requirements/base.txt` pin accordingly

## 2. HITL interrupt + SSE + resume/reject

- [ ] 2.1 Add interrupt **before** `create_note` / `update_note` NoteService side effects; leave search/summarize tools ungated; fail closed if checkpointer unavailable for mutations
- [ ] 2.2 Emit locked SSE `approval_required` (`type`, `tool`, `args`, `thread_id`, `interrupt_id`) then end the stream; document event ordering vs `tool_start` / `tool_end`
- [ ] 2.3 Add authenticated resume (approve) and reject endpoints under `/ai/agent*`; re-validate thread/checkpoint belongs to caller JWT workspace; deny cross-tenant; reject applies no mutation
- [ ] 2.4 Ensure non-stream `POST /ai/agent` returns a structured `approval_required` response for parity; keep `/ai/chat*` untouched
- [ ] 2.5 Add pytest coverage for interrupt-before-commit, approve path, reject path, and cross-workspace resume denial
- [ ] 2.6 Add operator script/curl smoke (`scripts/` or docs) proving approve vs reject on local `http://127.0.0.1`

## 3. Agent trajectory goldens

- [ ] 3.1 Add ≥5 trajectory cases under `evals/golden/` with `required_tools` / `forbidden_tools` / `sequence_mode`; include forbid-surprise-`create_note`
- [ ] 3.2 Extend `evals/run_eval.py` to assert trajectory constraints and include them in `PASS: X/Y`
- [ ] 3.3 Add fixtures so trajectory cases run under `--mode fixture` without live LLM keys; document in `evals/README.md`

## 4. Fixture evals in thin CI

- [ ] 4.1 Wire `python evals/run_eval.py --mode fixture` (with `PYTHONPATH=src`) into `.github/workflows/ci.yml` without live LLM or VPS secrets; failing fixtures fail the check
- [ ] 4.2 Verify locally that fixture evals + existing pytest still pass; confirm `docker-compose.yml` local path unbroken

## 5. Langfuse retrieval depth

- [ ] 5.1 Extend `observability.tracing` helpers to accept retrieved chunk/note ids + scores on spans/traces (no Langfuse SDK imports inside `src/ai/*`)
- [ ] 5.2 Update RagService (via tracing helpers) to log identities/scores; soft-no-op when Langfuse disabled; optional empty-retrieval score/marker
- [ ] 5.3 Document operator verification steps in `observe.md` / observability docs for local Langfuse inspection

## 6. Portfolio honesty + failure modes

- [ ] 6.1 Add failure-mode notes (empty retrieval, LLM 503/unavailable, embed lag) linked from runbook and/or interview talk track
- [ ] 6.2 Ensure README cost/latency table exists; fill from local Langfuse/sample when available and label **local/sample** (not production SLO)
- [ ] 6.3 Sync `goal.md` Tier 1 checkboxes / notes for HITL, Langfuse depth, trajectory, fixture CI, failure modes—without marking A-gate or hire-ready complete

## 7. Validation gate (local Alive)

- [ ] 7.1 Run focused pytest for HITL + any new observability unit tests
- [ ] 7.2 Run `evals/run_eval.py --mode fixture` and confirm trajectory + existing C-gate fixtures pass
- [ ] 7.3 Run HITL smoke script against local API; optionally confirm sibling FE chat/agent still Alive (Playwright)—approval UI not required
- [ ] 7.4 Spot-check: chat routes unchanged; no production-live claims in README/`goal.md`
