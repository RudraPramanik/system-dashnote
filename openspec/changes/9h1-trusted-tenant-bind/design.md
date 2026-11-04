## Context

See proposal.md for motivation. Agent tools today take `workspace_id`, `user_id`, and `role` as StructuredTool args (`src/ai/tools/schemas.py`, `note_tools.py`); the system prompt in `workspace_assistant.py` tells the model to pass them from state. Graph state already freezes tenant fields at invoke (`ai/workflows/state.py`; routes inject from JWT in `ai_routes/agent.py`), but tool wrappers still accept model-supplied copies. Mutation tools already use a `contextvars.ContextVar` for the DB session — a natural parallel for harness context. Blueprint order: implement only **9H.1** substages from `docs/documentation/blueprint/slice9_trust.md`.

## Goals / Non-Goals

**Goals:**
- One trusted `HarnessContext` per agent invoke, sourced from JWT `RequestContext`
- Tools call NoteService/RagService with tenant from that context only
- HITL approval payloads show bound tenant identity
- Automated regression without a live LLM key

**Non-Goals:**
- 9H.2 typed error envelopes / note ACL mapping beyond what bind needs for a simple deny
- 9H.3 delimiters, 9H.4 budgets, 9H.5 control plane, 9H.6 full grade suite
- Changing `/ai/chat*` or resume/reject HTTP contracts beyond filling approval tenant fields
- New permission engine, Alembic, compose changes

## Decisions

### 1. HarnessContext shape and injection
**Choice:** Small dataclass/TypedDict in `ai` (e.g. `ai/harness/context.py` or adjacent to tools/workflows) with `workspace_id`, `user_id`, `role`, optional `trace_id`, optional budget placeholders (unused until 9H.4). Build once in agent routes from `RequestContext`; store on graph state **and** set a `contextvars.ContextVar` before tool execution (same pattern as `db_session_var`).  
**Why:** Tools already cannot take FastAPI deps; contextvars match the existing session injection. Graph state keeps checkpoint/resume aligned with JWT-checked workspace.  
**Alternatives:** Closure-bound tools rebuilt per request (harder with Shared StructuredTool registry); only graph state without contextvars (fragile if tool node does not forward state into kwargs).

### 2. Schema omit preferred over overwrite
**Choice:** Remove `workspace_id` / `user_id` / `role` from Pydantic tool schemas and tool function signatures; read them only from HarnessContext inside wrappers. Update system prompt so it no longer instructs the model to pass tenant fields.  
**Fallback:** If StructuredTool/LangChain binding still requires the fields after inventory (9H.1.1), keep schemas but overwrite from HarnessContext immediately before service calls and log mismatches.  
**Why:** Blueprint preferred path; removes the attack surface instead of papering over it.  
**Alternatives considered:** Prompt-only “do not modify” (current — rejected).

### 3. Deny string for missing context
**Choice:** Return a clear tool-result denial string (e.g. containing `forbidden` or an existing deny phrase) without inventing the full 9H.2 envelope enum.  
**Why:** 9H.2 owns the stable error code set; 9H.1 only needs fail-closed behavior.

### 4. HITL payload
**Choice:** After bind, when building interrupt/`approval_required` args, copy tenant fields from HarnessContext into the args object (keep current JSON keys for UI stability). Document as server-authored in code comment or adjacent doc touch if needed. Do not widen resume checks.  
**Why:** Matches 9H.1.3 fallback; preserves product UI contract.

### 5. Proof without live LLM
**Choice:** Prefer a focused unit/integration test that invokes the tool wrapper (or tool node helper) with mismatched model args and asserts service kwargs / deny. Add a fixture case only if the existing eval runner can load it without a provider key; otherwise point the blueprint theme at the unit test.  
**Why:** 9H.1.4 allows unit-test fallback; CI must not need live keys.

### 6. Work sequencing inside this change
**Choice:** Tasks follow Composer substages: inventory (doc-only in change notes or short comment inventory) → bind → HITL → golden. Apply sessions can still be one substep at a time.  
**Why:** Matches `slice9_H.md` / `slice9_trust.md` law.

## Risks / Trade-offs

- [Schema omit breaks evals/scripts that pass tenant in tool args] → Update those callers in the same change; inventory first.
- [Overwrite fallback hides model bugs] → Log when model tenant ≠ harness tenant.
- [ContextVar leak across concurrent requests] → Set/reset in the tool-execution node around the call; never leave a stale default across awaits without proper scoping (mirror db_session_var discipline).
- [Partial bind leaves prompt still asking for tenant fields] → 9H.1.2 must update prompt + schemas together.
- [Scope creep into 9H.2 ACL] → Deny only missing context / keep role unused for authorization until 9H.2.

## Migration Plan

1. Inventory (no runtime change).
2. Land HarnessContext + bind/overwrite behind existing agent routes; keep chat routes unchanged.
3. Update HITL args construction; re-run existing HITL tests.
4. Add invented-workspace test; green CI without LLM key.
5. Rollback: revert the change PR; no DB migration. Feature flags not required for this slice.

## Open Questions

- Exact module path for `HarnessContext` (`ai/harness/` vs next to `ai/tools/`) — decide at apply from existing package layout; does not change specs.
- Whether any external eval JSON already hard-codes tenant tool args — discover during 9H.1.1 inventory.
