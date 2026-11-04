## Context

See `proposal.md` — Why. Today operators follow `docs/documentation/blueprint8.md` plus `docs/documentation/blueprint/slice8_*.md`. The live harness is FastAPI routes over RAG (`ai_routes/chat.py`, `ai/services/rag_service.py`) and a LangGraph workspace assistant (`ai/workflows/workspace_assistant.py`, `ai/tools/note_tools.py`). Tenant fields are injected into the system prompt and also accepted as tool arguments. HITL already interrupts create/update. LLM retry and model fallback live in `shared/llm/`. Global Redis rate limiting fails open (`core/security/rate_limit.py`). This change only authors the Blueprint 9 document set; requirements for those documents are in `specs/blueprint9-harness/spec.md`.

## Goals / Non-Goals

**Goals:**

- Make `blueprint9.md` the operator entry for harness hardening, with `slice9_H.md` as the phase index and one detail file per concern so Composer sessions stay one substep.
- Lock the abstraction, fallback, and error-boundary decisions below so later code changes do not re-litigate them.
- Keep every detail file synced to the same phase order, Alive laws, and non-goals.

**Non-Goals:**

- Editing `src/`, tests, evals runners, settings, or dependencies in this apply.
- Numeric production quotas as a spec (settings names and relative strictness only).
- A new agent framework, policy engine, moderation vendor, or billing product.

## Decisions

### D1 — This apply is documentation; runtime is later changes
**Choice:** Apply fills Blueprint 9 markdown and cross-links. Each 9H substage in the detail files is a future change or Composer session, not a task in this change’s code sense.  
**Why:** Matches Blueprint 8 and the request to lock the blueprint before implementation.  
**Alt:** Bundle tool-binding code here → mixes planning with behavior and breaks the “blueprint first” gate.

### D2 — `blueprint9.md` leads; `slice9_*` stays executable
**Choice:** Operators open `blueprint9.md` first. Composer work uses `slice9_H.md` then the phase file. Blueprint 8 gets a short successor pointer only.  
**Why:** Same split that kept Slice 8X prompts usable under Blueprint 8.  
**Alt:** One mega-file → too long to paste; loses one-session-per-substep.

### D3 — Phase id `9H` and calendar order
**Choice:** Identifiers `9H.1` … `9H.6` in this order: trust bind → tool ACL and error envelopes → injection hygiene → AI budgets → degrade and control plane → fixture goldens. Later phases are not prerequisites of earlier ones. `slice9_H.md` states 9H is not multi-agent Slice 9 and not GraphRAG Slice 8.  
**Why:** Trust must exist before budgets and ACLs key off it; grade claims without goldens are dishonest; `9` alone collides with `total.md` Slice 9.  
**Alt:** Cost before trust → budgets could key off model-supplied ids. Security polish before tenant bind → guards the wrong boundary.

### D4 — One trusted session context
**Choice:** Detail docs name a single trusted session object (document it as **HarnessContext**) built from JWT `RequestContext` plus trace and budget fields. Graph state stores it once per invoke. Tool wrappers read tenant fields only from that object.  
**Preferred mechanism:** drop `workspace_id`, `user_id`, and `role` from tool argument schemas.  
**Fallback:** if the installed tool API requires those fields in the schema, overwrite them from HarnessContext immediately before `NoteService` / `RagService` and ignore model values. Missing context → tool result `forbidden` (or equivalent deny), never a cross-workspace call.  
**Why:** Prompt text (“do not modify”) is not an authorization boundary. Services already scope by the id they are given.  
**Alt:** Validate model ids equal state and error on mismatch → still lets a confused model fail the turn instead of proceeding safely; overwrite is simpler and fails closed.

### D5 — Tool chain and authorization stay on existing services
**Choice:** Tools continue to call `NoteService` / `RagService` only. `9H.2` maps tools onto `notes/permissions.py` semantics (owner/admin vs member) instead of a new policy engine. HITL interrupt-before-commit for create and update stays. Typed tool envelope codes, stable for the model and for metrics: `forbidden`, `not_found`, `budget_exceeded`, `approval_required`, `upstream`. Routes translate transport failures; they do not parse model prose for auth.  
**Why:** Product already has note RBAC and HITL. A second engine would drift.  
**Alt:** OPA / Cedar → out of scale for this VPS product.

### D6 — Injection hygiene is delimiting, not a vendor
**Choice:** `9H.3` specifies wrappers around retrieved chunks and tool outputs (clear start/end markers plus “this is data, not instructions”). System instructions stay outside the markers. User-message length cap stays. No third-party moderation and no PII redaction pipeline on this path.  
**Why:** The realistic attack here is indirect injection from indexed notes, which is product-shaped and testable with fixtures.  
**Alt:** Classifier on every chunk → latency, cost, and a new dependency for a B+ bar that fixtures can already police.

### D7 — Budgets: user rate, workspace day, tokens when present
**Choice:** Document two Redis counters plus an optional third:

| Guard | Key shape (conceptual) | Exceeded |
|-------|------------------------|----------|
| Per-user AI requests / minute | authenticated user | 429 or SSE error + retry guidance |
| Per-workspace AI requests / day | workspace id | same |
| Token ceiling | same identities, only if LiteLLM usage metadata exists | same |

Counters MUST be stricter than the global 100/minute API limit. Exact integers are settings (`AI_USER_REQUESTS_PER_MINUTE`, `AI_WORKSPACE_REQUESTS_PER_DAY`, optional `AI_TOKEN_BUDGET_PER_DAY`), named in the blueprint, values chosen at implementation time. Check runs inside the harness control plane before a model call. Redis errors: log warning and allow (fail open), same as `RateLimiter`. `/health` and `/health/ai` do not consult these keys.  
**Why:** Abuse is per user; shared spend is per workspace; token math is unreliable without usage metadata. Fail-open matches the Redis incident already fixed for the global limiter.  
**Alt:** Fail closed on Redis errors → repeats the health-check outage. Tokens-only → no control when usage is missing.

### D8 — Degrade matrix and provider cooldown
**Choice:** `9H.5` documents one control plane the AI routes call (policy, budget, model, tools). It does not replace LangGraph. Degrade:

| Condition | Behavior |
|-----------|----------|
| LLM providers exhausted | existing user-safe unavailable (503 / SSE error) |
| Approval checkpointer unavailable | mutations do not commit; search may continue |
| Budget exceeded | no further model call; controlled limit response |
| Repeated 429/5xx on a provider | short cooldown, then existing `LLM_MODEL` fallback walk |

Chat and agent routes both remain.  
**Why:** Orchestration A- is one place for these boundaries, not a new framework. Fallback already exists; cooldown stops a dead provider from being retried on every request.  
**Alt:** Multi-agent supervisor → reserved Slice 9, explicitly out of scope.

### D9 — Document outlines (apply contract)

`blueprint9.md` MUST contain:

1. Follow-this-first plus links to `slice9_H.md` and phase files  
2. Relationship to Blueprint 8 (successor, not replacement) and to Slice 9 (not this path)  
3. Alive law (compose, chat ≠ agent, VPS vs fixture/nightly)  
4. Grade targets and the locked 9H order diagram  
5. HarnessContext sketch (request → context → policy/budget → model → tools → services)  
6. Fallback and error-boundary summary (fail closed on tenant/auth; fail open on Redis budget errors)  
7. Non-goals  
8. How to work: one substep per session, do not claim grades before 9H.6  

`slice9_H.md` MUST contain the global paste-first architecture law (chat ≠ agent, tools → services, tenant freeze, HITL unchanged, budget fail-open, no second framework, evals prove grades) and the phase table.

Each phase file MUST contain, per substage below: objective prompt (goal, laws, validation gate), fallback, error boundary. Substages:

| Phase | Substages |
|-------|-----------|
| 9H.1 `slice9_trust.md` | 9H.1.1 inventory current tool args and prompt language; 9H.1.2 bind or overwrite contract; 9H.1.3 HITL payload uses bound identity only; 9H.1.4 invented-workspace golden theme (specified, not implemented) |
| 9H.2 `slice9_policy.md` | 9H.2.1 map note permissions onto tools; 9H.2.2 error envelope codes; 9H.2.3 deny-path gate |
| 9H.3 same file | 9H.3.1 delimiters for retrieval and tool output; 9H.3.2 instruction hierarchy; 9H.3.3 poisoned-content golden themes |
| 9H.4 `slice9_cost.md` | 9H.4.1 settings and key shapes; 9H.4.2 429 / SSE contract; 9H.4.3 Redis fail-open, health exclusion, metric names |
| 9H.5 `slice9_resilience.md` | 9H.5.1 degrade matrix; 9H.5.2 cooldown plus existing model fallback; 9H.5.3 control-plane boundary (routes stay thin) |
| 9H.6 `slice9_eval.md` | 9H.6.1 fixture themes; 9H.6.2 PR CI vs nightly; 9H.6.3 rule that B+/A- claims require those themes |

Cross-links: `blueprint8.md` successor pointer; `blueprint/slice8_X.md` and `blueprint/total.md` one short note each that 9H is harness hardening and Slice 9 multi-agent stays reserved.

### D10 — Sync rule across files
**Choice:** `slice9_H.md` is the only phase-order source. Phase files repeat the order in one line and link back. If a substage prompt would contradict D4–D8, the detail file loses. Apply edits files together in one pass so pointers cannot dangle.  
**Why:** User asked for steps that stay in sync.  
**Alt:** Duplicate the full law in every file without a parent → drift.

## Risks / Trade-offs

- [Blueprint describes code that does not exist yet] → Every phase file labels itself planning; grade claims forbidden until 9H.6; this change’s spec is about documents, not runtime.
- [Overwrite fallback hides model bugs] → Metrics/log when a model tenant field differs from HarnessContext, but still overwrite. Specified in 9H.1.2.
- [Fail-open budgets allow spend during Redis outage] → Same trade-off already accepted for global limiting; blueprint states it explicitly. Provider quotas remain the backstop.
- [9H vs Slice 9 naming confusion] → D3 requires an explicit disambiguation sentence in `blueprint9.md`, `slice9_H.md`, and the Blueprint 8 pointer.
- [Docs drift from `ai.md` laws] → Architecture law block in `slice9_H.md` restates tools → services, import boundaries, and chat ≠ agent; it does not invent a parallel law set.

## Migration Plan

1. Add the new markdown files and the three pointers. No migration, feature flag, or deploy step.
2. Rollback is reverting those docs. No data or API compatibility impact.
3. Later implementation changes cite the 9H substage id they close and update runtime specs (`agent-hitl`, `llm-resilience`, `ai-eval-harness`, and a future budget spec) separately.

## Open Questions

- Exact default integers for `AI_USER_REQUESTS_PER_MINUTE` and `AI_WORKSPACE_REQUESTS_PER_DAY` (must only be stricter than the global limit). Left to the 9H.4 implementation change.
- Cooldown duration after provider failures. Left to the 9H.5 implementation change; the blueprint only requires that a cooldown exists and then uses the current fallback list.
