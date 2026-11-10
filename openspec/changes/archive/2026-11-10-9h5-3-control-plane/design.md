## Context

See proposal.md for why. Runtime contracts live in the new `ai-harness-control-plane` delta and the `ai-harness-degrade` fence update.

Today:
- `ai_routes/chat.py` calls `consume_ai_request_budget` directly on unary and stream, then maps `LLMUnavailableError` to 503 / SSE.
- `ai_routes/agent.py` binds `HarnessContext` via `_bind_harness_context`, sets `budget_redis_var`, and maps `BudgetDenied` / `LLMUnavailableError` in each handler (`/agent`, `/agent/stream`, `/agent/resume`, `/agent/reject`).
- Implementations already exist: `ai.harness.context`, `ai.harness.budget_check`, `shared.llm.fallback` (including 9H.5.2 cooldown). There is no `control_plane` module yet.
- Degrade matrix rows (9H.5.1) and cooldown (9H.5.2) are already proven. This substep consolidates ownership, not new client contracts.

Process ownership stays on the API. The ARQ worker does not participate. No Qdrant read/write. Collections stay `notes_chunks` / `files_chunks`. No Alembic. No compose change. No new budget Redis key scheme.

Import law: `src/ai/*` may use `config`, `ai.*`, `shared.*`, stdlib, third-party — not FastAPI HTTPException helpers if that would pull routes into the harness. Prefer typed denials the route layer maps.

## Goals / Non-Goals

**Goals:**

- One harness module both chat and agent routes call for trusted-context construction, budget gate, and known denial types.
- Routes become thin: parse request, call plane, map typed outcomes to HTTP / SSE.
- Preserve existing 429 / `budget_exceeded`, 503 / unavailable, citation, and HITL behavior.

**Non-Goals:**

- Rewriting cooldown, fallback candidate order, or HITL checkpointer probe ownership.
- Merging `/ai/chat*` into `/ai/agent*` or adding a second agent framework.
- 9H.6 fixture packaging / grade claims.
- Moving RagService or LangGraph into the control-plane module as reimplementations.
- New Prometheus series, Alembic, compose, or Langfuse SDK imports inside `src/ai/*`.

## Decisions

### 1. Module name: `ai.harness.control_plane`

**Choice:** Add `src/ai/harness/control_plane.py` as the documented harness control plane. Keep `budget_check.py` and `context.py` as the leaf implementations it calls.

**Why:** Matches prior 9H.5.1/9H.5.2 “do not half-build `control_plane.py`” fence and the blueprint wording. One obvious import for routes.

**Alternatives:** Put helpers only in `ai/harness/__init__.py` (unclear ownership — rejected). Name it `session.py` (collides with DB mental model — rejected).

### 2. Two families of entrypoints, not one mega-function

**Choice:** Expose small helpers the routes compose, rather than one function that owns all streaming generators:

- Context: bind / reset `HarnessContext` (and agent’s `budget_redis_var` where still required for mid-turn graph checks).
- Gate: run `consume_ai_request_budget` once for chat unary/stream entry (agent mid-turn checks stay where 9H.4.2 put them — inside the model node — but denial mapping uses shared helpers).
- Denial mapping: shared predicates / payload builders for budget denied and provider unavailable so routes do not re-copy SSE / HTTPException detail strings.

If a clean `run_chat` / `run_agent` that returns results without swallowing HITL/SSE generators is feasible without a rewrite, prefer that; otherwise two thin prep + map helpers in the same module still satisfy the blueprint fallback.

**Why:** Agent stream / resume / reject have HITL and SSE shapes that should not be rewritten in one session. The blueprint explicitly allows two functions in one module.

**Alternatives:** Force a single `run_ai(request)` that yields every SSE frame (large rewrite risk — rejected for 9H.5.3). Leave budget calls duplicated but extract only 503 mapping (fails “no inline Redis budget keys in routes” gate — rejected).

### 3. Control plane raises or returns typed denials; routes map status codes

**Choice:** Keep FastAPI `HTTPException` and StreamingResponse construction in `ai_routes/*`. The plane returns `BudgetDecision` / raises existing `BudgetDenied` / surfaces `LLMUnavailableError` (or a thin harness wrapper that preserves those types). Routes map:

| Denial | Unary | Stream |
|--------|-------|--------|
| Budget denied | 429 + Retry-After when known | SSE `budget_exceeded` then end |
| Provider unavailable | 503 + `LLM_UNAVAILABLE_MESSAGE` | SSE error with that message |
| Forbidden / missing trusted context | existing 403 / tool `forbidden` path | unchanged |

**Why:** Import law and prior slices keep HTTP in routes. Do not drag FastAPI into `src/ai/harness`.

**Alternatives:** Raise HTTPException from harness (violates ai import boundary — rejected).

### 4. Resume / reject still bind context through the plane; reject still skips budget spend

**Choice:** `/ai/agent/resume` and `/ai/agent/reject` call the same context-bind helper. Reject MUST NOT consume AI request budget (already 9H.4.2). Resume continues to hit model-node budget checks as today.

**Why:** Thinning means shared bind/reset, not inventing new spend rules.

**Alternatives:** Leave resume/reject with local `_bind_harness_context` only (partial duplication remains — weaker than blueprint “both use” — rejected).

### 5. Cooldown and checkpointer stay where 9H.5.1 / 9H.5.2 left them

**Choice:** Do not move provider cooldown into the control plane. Do not move `_ensure_checkpointer_for_mutation` into the control plane. The plane only ensures generation routes surface total exhaustion and budget denials consistently.

**Why:** Blueprint 9H.5.3 goal is route thinning for policy/budget/provider-unavailable mapping. Tool-level HITL and fallback cooldown are already correct.

**Alternatives:** Centralize checkpointer probe in the plane (spills into tool package — rejected).

## Risks / Trade-offs

- [Over-extracting streaming into the plane breaks HITL SSE] → Prefer shared gate + map helpers first; only wrap full generators if citation/HITL tests stay green without a rewrite.
- [Agent mid-turn budget still lives in the model node] → That is intentional (9H.4.2). Control plane owns route-entry duplication and shared denial mapping, not a second counter.
- [Routes still import `LLMUnavailableError` for `except`] → Acceptable if the type is the shared contract; do not reimplement message strings in each route.
- [Test churn on chat/agent suites] → Reuse `tests/ai/test_harness_budget_refusal.py`, `test_harness_degrade.py`, citation and HITL tests; add a thin assertion that route modules do not call `consume_ai_request_budget` directly (import/grep-style unit or a facade-only export).

## Migration Plan

1. Add `control_plane.py` helpers; switch chat then agent routes to use them in one API deploy.
2. No schema, env, or compose change. Clients see the same status codes and SSE shapes.
3. Rollback reverts route imports to the previous direct calls; leaf budget/context modules remain.

No open questions.
