# Slice 9H.5 — Degrade Modes and One Control Plane
## Composer substages (matrix → cooldown → thin routes)

> **Parent index (order source):** [`slice9_H.md`](slice9_H.md) — phase **9H.5**, calendar position 5th.  
> **Operator default:** [`../blueprint9.md`](../blueprint9.md).  
> **Code anchors:** `src/shared/llm/fallback.py` · `src/shared/llm/retry.py` · `src/ai/memory/checkpointer.py` · `src/ai_routes/chat.py` · `src/ai_routes/agent.py` · `src/ai/workflows/workspace_assistant.py`  
> **Goal:** One harness path decides policy, budget, model, and tool binding. Existing LangGraph and RAG stay. Degrade is explicit.  
> **This file is a prompt blueprint.** Implementing the code is a later apply of these substages.

Order reminder: 9H.1 → 9H.2 → 9H.3 → 9H.4 → 9H.5 → 9H.6. This phase does not add a second agent framework.

---

## Degrade matrix (locked)

| Condition | Behavior |
|-----------|----------|
| All model providers exhausted | User-safe unavailable: HTTP 503 or SSE error. No empty 200. |
| Approval checkpointer unavailable | create/update do not commit. Search-style tools may still run. |
| AI budget exhausted | No further model call for that identity. 429 or SSE `budget_exceeded` (9H.4). |
| Repeated 429/5xx on one provider | Short cooldown for that provider, then the existing `LLM_MODEL` / `LLM_MODEL_FALLBACKS` walk. |

Chat and agent routes both remain.

---

## Sub-step 9H.5.1 — Degrade matrix in code

**Goal:** The three runtime rows (provider down, checkpointer down, budget down) match the table. Cooldown is the next substep.

**Fallback:** Checkpointer-down already blocks mutations in places; this substep documents and tests that search can continue, and closes any path that still commits without a checkpointer.

**Error boundary:** Mutation without a checkpointer is a bug. Fail closed (no commit). Search failure still returns the existing empty-retrieval copy rather than 500 when retrieval itself is empty.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.5.1 — Encode the degrade matrix except provider cooldown.

Paste ARCHITECTURE LAW — Slice 9H first.

GOAL:
  Make these behaviors true and tested:
  - Provider failure after existing fallbacks → 503 or SSE error, user-safe text, never silent empty 200.
  - Checkpointer unavailable → create_note and update_note do not commit; search_notes may still answer.
  - Budget exhausted → the 9H.4 refusal, and no provider completion.
  Keep /ai/chat* and /ai/agent* both mounted.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT add a second agent framework or a multi-agent supervisor.

VALIDATION GATE:
  Tests or existing smokes cover provider-unavailable and checkpointer-down.
  Checkpointer-down test asserts no note commit.
  A search call in that mode may still return a normal answer or the empty-retrieval copy.

FALLBACK:
  If checkpointer-down cannot be simulated in-process, gate the mutation tools with the
  same probe the HITL path already uses and unit-test that probe.

ERROR BOUNDARY:
  Mutation tools fail closed without checkpointer. They must not write "just this once".
```

---

## Sub-step 9H.5.2 — Provider cooldown, then existing fallback

**Goal:** After repeated rate-limit or upstream failures, skip that provider for a short cooldown, then walk the current fallback list.

**Fallback:** Cooldown duration is an implementation setting (for example `LLM_PROVIDER_COOLDOWN_SECONDS`). The blueprint does not lock the integer. If cooldown storage is awkward, an in-process timestamp is enough for one API process; document that it is per process.

**Error boundary:** Cooldown must not stick forever. When the timer ends, the provider is eligible again. If every provider is in cooldown, return the same user-safe unavailable response as total provider failure.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.5.2 — Cooldown a failing provider, then use LLM fallbacks.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: existing shared/llm fallback walk. Read it before editing.

GOAL:
  After repeated 429 or 5xx from one model id, mark it cooling down.
  The next request skips it and continues the existing LLM_MODEL fallback order.
  When cooldown ends, the id is eligible again.
  Do not remove the current fallback list.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT add a new inference vendor as part of cooldown.

VALIDATION GATE:
  A unit test marks the primary id in cooldown and asserts the next completion
  uses the next fallback id. A second test shows the primary is used again after expiry.

FALLBACK:
  Store cooldown in memory on the API process. Document that multiple workers
  do not share it. Do not require Redis for cooldown (budget Redis is a different concern).

ERROR BOUNDARY:
  If all candidates are cooling down or failing, return the existing user-safe
  unavailable response. Do not loop forever.
```

---

## Sub-step 9H.5.3 — Control-plane boundary

**Goal:** AI routes call one harness entry for “may I run, then run” instead of each route reimplementing budget, tenant bind, and provider policy. LangGraph remains the agent loop.

**Fallback:** A thin module (name it in code, document it as the harness control plane) that chat and agent routes both call. If a single function cannot wrap streaming and unary without a rewrite, two functions in the same module (`run_chat`, `run_agent`) still count, as long as budget and tenant policy are not copied into both route files.

**Error boundary:** Routes catch harness denials and map them to 429, 403, or 503. They do not catch-all into 500 for those codes.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.5.3 — Thin routes, one harness control plane.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.1 bind, 9H.4 budget check, 9H.5.1 degrade behavior exist or are stubbed behind the same module.

GOAL:
  Move budget check, trusted-context construction, and provider-unavailable mapping
  behind one module that /ai/chat* and /ai/agent* both use.
  The LangGraph workspace assistant stays the agent implementation.
  RagService stays the fast path implementation.
  Routes parse HTTP and SSE only.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT introduce a second agent framework.
  src/ai/* must not import the Langfuse SDK. Tracing stays in observability.tracing.

VALIDATION GATE:
  Route modules no longer instantiate their own Redis budget keys inline.
  A denial from the harness module is what produces 429 or 503.
  Existing chat citation behavior and agent HITL events still pass their tests.

FALLBACK:
  Two functions in one module (unary/stream or chat/agent) are acceptable.
  Copy-pasting the budget check into both route files is not.

ERROR BOUNDARY:
  Map forbidden, budget_exceeded, and upstream/provider-down to their HTTP or SSE
  statuses. Unexpected exceptions may still be 500, but the three known denials must not be.
```
