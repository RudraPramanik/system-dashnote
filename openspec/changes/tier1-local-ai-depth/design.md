## Context

See `proposal.md` for motivation. Local Compose + sibling FE already demo the Alive path; C-gate `evals/` exists; agent graph (`workspace_assistant.py`) + `note_tools.py` mutate via `NoteService` with checkpointer support; SSE events live in `ai_routes/agent.py` (`token` | `tool_start` | `tool_end` | `done` | `error`). VPS A-gate is deferred; this design follows blueprint8’s **AI-depth-first** alternate while keeping code production-ready for later promote.

Constraints that shape the approach: `rules.md` / OpenSpec context (no `from src.*`, tools → services, chat≠agent, Langfuse only via `observability.tracing`), `slice8_hitl.md` locked SSE contract, no new `pending_actions` table, thin CI must stay secret-free.

## Goals / Non-Goals

**Goals:**
- Production-ready HITL interrupt/resume/reject on `/ai/agent*` validated locally (script + pytest).
- Trajectory goldens + fixture CI gate without live LLM keys.
- Langfuse retrieval-depth enrichment through observability helpers.
- Operator honesty: local Tier 1 ≠ production-live / hire-ready.

**Non-Goals:**
- VPS TLS/smoke, FE deploy, polished Next.js approval UI.
- Replacing golden harness with Langfuse experiments / RAGAS / DeepEval.
- GraphRAG, multi-agent supervisor, automation-queue conflation with agent HITL.
- Changing `/ai/chat*` into an agent.

## Decisions

### 1. Pending state = LangGraph checkpointer (not a new table)
- **Choice:** Reuse `AsyncPostgresSaver` / existing `init_checkpointer` + `thread_id` for interrupt state.
- **Why:** Matches `slice8_hitl` law; avoids dual persistence; survives process restart on Postgres-backed checkpoint.
- **Alternatives:** `pending_actions` table (rejected—forbidden for this gate); Redis-only pending (weaker durability / second source of truth).

### 2. Interrupt API = version-grounded LangGraph interrupt
- **Choice:** Read installed `langgraph` version first; use that version’s interrupt primitive (e.g. `interrupt()` / dynamic interrupts) **before** `NoteService.create_note` / `update_note` commits. Prefer wrapping mutation tool execution rather than post-commit rollback.
- **Why:** Pin is currently loose (`langgraph>=0.1.0`); guessing APIs breaks at runtime.
- **Alternatives:** Always-approve feature flag only (insufficient for Tier 1 proof); FE confirm without graph interrupt (not durable / not API-first).

### 3. SSE lifecycle = emit `approval_required` then close stream
- **Choice:** Locked payload `{type, tool, args, thread_id, interrupt_id}`; then end SSE (same spirit as `done` + `[DONE]`). Resume/reject are separate authenticated HTTP endpoints under `/ai/agent*` (exact paths chosen at implement time, documented in OpenAPI/docs).
- **Why:** Avoids proxy timeouts from holding streams open; matches blueprint; FE can reconnect later.
- **Alternatives:** Long-lived stream waiting for approval (fragile behind nginx); WebSocket channel (out of scope).

### 4. Tenancy on resume = JWT workspace + thread ownership re-check
- **Choice:** On resume/reject, load checkpoint/thread metadata and deny unless it belongs to `RequestContext.workspace_id` (and appropriate user ownership rules already used by `_resolve_thread_id`). Never trust model args for `workspace_id` / `user_id` / `role`.
- **Why:** Prevents cross-tenant resume by guessing `thread_id`.
- **Alternatives:** Trust only graph state without re-check (unsafe if client supplies arbitrary thread id).

### 5. Validation pyramid for local Tier 1
```
PR CI (no live LLM)          Local operator (Compose)
─────────────────────        ─────────────────────────
pytest (HITL unit/API)       smoke script: interrupt → approve/reject
fixture run_eval.py          live trajectory optional
docker build                 Playwright FE: chat/agent still Alive
                             (approval UI not required)
```
- **Choice:** Gate CI on fixtures + unit/API tests; prove live HITL with script against `http://127.0.0.1`; optional Playwright only to assert Alive (no polished approve UI).
- **Why:** Production-ready without requiring VPS or paid keys in PR.
- **Alternatives:** Block CI on live agent calls (rejected—breaks thin CI law).

### 6. Langfuse depth via tracing helpers only
- **Choice:** Extend span/trace payloads in `observability.tracing` (+ call sites in RagService that already use tracing) to include retrieved ids + scores; optional empty-retrieval score. Soft-disable when Langfuse off.
- **Why:** Preserves “no Langfuse SDK in `src/ai/*`”.
- **Alternatives:** Direct SDK in RagService (violates observe/rules).

### 7. Trajectory goldens as first-class JSONL theme
- **Choice:** Add `evals/golden/` trajectory cases (≥5) with `required_tools` / `forbidden_tools` / `sequence_mode`; extend `run_eval.py` assertions; fixtures for CI.
- **Why:** Blueprint8 Tier 1 #6; informs what HITL must still catch.
- **Alternatives:** Manual e2e only (not CI-regressible).

### 8. Docs mark AI-depth-first window
- **Choice:** Update `goal.md` / blueprint8 / ship-plan notes to record active local Tier 1 window; keep A4/A7 unchecked; label cost/latency as local sample.
- **Why:** Prevents premature hire claims while unlocking deepeners.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LangGraph interrupt API mismatch vs pin | First implement task: inventory installed version; tighten `requirements` pin to the API used |
| Checkpointer degraded mode (no Postgres saver) | Fail closed for mutations when HITL required—do not silently mutate without interrupt persistence; log clearly |
| Partial tool_start before interrupt confuses clients | Document ordering: interrupt before NoteService commit; may follow `tool_start`; never emit `tool_end` success for committed mutation without approval |
| Fixture trajectory drifts from live agent | Keep ≥1 live local script path; fixtures assert contract, not model creativity |
| Scope creep into FE approval console | Explicit non-goal; script/tests are the gate |
| Claiming hire-ready early | Spec + README honesty requirements; A-gate remains open |

## Migration Plan

1. Land interrupt + SSE + resume/reject behind existing agent routes (backward compatible: non-mutation traffic unchanged; mutation clients must handle `approval_required`).
2. **BREAKING for mutation clients:** streaming clients that assume create/update always complete in one SSE session must handle interrupt + resume. Document in `ai.md` / API notes; chat clients unaffected.
3. Add tests + `scripts/` HITL smoke; wire fixture evals into `ci.yml`.
4. Enrich Langfuse payloads; fill local cost/latency sample when traces exist.
5. Later (out of this change): promote same builds to VPS; re-run smoke; then claim A-gate.

**Rollback:** Feature-flag or settings switch to bypass HITL only if needed for emergency demo—default remains interrupt-on for create/update once shipped; prefer revert commit over silent auto-approve in prod.

## Open Questions

- Exact resume/reject URL paths (`/ai/agent/resume` vs nested under thread id)—finalize during implement against existing router style; must stay under `/ai` auth.
- Whether non-stream `POST /ai/agent` returns a structured `approval_required` body (likely yes for parity)—confirm while implementing stream first per blueprint.
