# Slice 9H — Harness Hardening Index
## Detail index (trust → ACL → injection → budgets → degrade → goldens)

> **Operator default for this path:** [`../blueprint9.md`](../blueprint9.md). **This file is the only phase-order source.** If a phase file disagrees, this file wins.  
> **Not Slice 8 and not Slice 9.** Slice **8** = optional GraphRAG. Slice **9** = multi-agent supervisor (reserved, later). **9H** is harness hardening on the existing chat and agent surfaces.  
> **Ship / hire default** remains [`../blueprint8.md`](../blueprint8.md). 9H does not change Tier 0 order.  
> **When to run:** After the product is alive (API, `/ai/chat*`, `/ai/agent*`, HITL). One Composer session ≈ one substep. Later phases are not prerequisites of earlier ones.

| Phase ID | Work package | Detail blueprint | Calendar position |
|----------|--------------|------------------|-------------------|
| **9H.1** | Trusted tenant bind | [`slice9_trust.md`](slice9_trust.md) | 1st |
| **9H.2** | Tool ACL + error envelopes | [`slice9_policy.md`](slice9_policy.md) | 2nd |
| **9H.3** | Injection hygiene | [`slice9_policy.md`](slice9_policy.md) | 3rd |
| **9H.4** | AI budgets | [`slice9_cost.md`](slice9_cost.md) | 4th |
| **9H.5** | Degrade + control plane | [`slice9_resilience.md`](slice9_resilience.md) | 5th |
| **9H.6** | Fixture goldens | [`slice9_eval.md`](slice9_eval.md) | 6th (proof gate) |

**Also:** [`../blueprint9.md`](../blueprint9.md) · [`../blueprint8.md`](../blueprint8.md) · [`total.md`](total.md)

---

## ARCHITECTURE LAW — Slice 9H
### Paste as the FIRST message in every 9H Composer session, then paste one substep prompt

```
ARCHITECTURE LAW — DashNoteSystem Slice 9H (harness hardening).

THIS IS NOT SLICE 9:
  9H hardens the existing workspace assistant.
  Multi-agent supervisor productization stays reserved as Slice 9.
  GraphRAG / Neo4j (Slice 8) is out of scope.

CHAT ≠ AGENT:
  /ai/chat* remains the fast RAG path.
  /ai/agent* remains the tool loop.
  Do NOT replace /ai/chat* with /ai/agent*.

DO NOT BREAK LOCAL DEV:
  docker-compose.yml remains the FULL local stack
  (db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT break local docker compose.

TOOL CHAIN:
  Tools call NoteService or RagService only.
  Never call repositories from tools or from the harness control plane.

TENANT FREEZE:
  workspace_id, user_id, and role come from HarnessContext
  (JWT request context frozen for the invoke).
  Model tool arguments MUST NOT override tenant identity.
  Missing HarnessContext → deny the tool. Never guess a workspace.

HITL UNCHANGED:
  create_note and update_note still interrupt before any commit.
  Resume/reject still checks the thread belongs to the caller workspace.

BUDGET:
  AI budget checks fail open on Redis errors (log a warning, allow).
  They fail closed when the counter is over the limit (429 or SSE error).
  /health and /health/ai do not depend on AI budget keys.

ONE CONTROL PLANE:
  Do not add a second agent framework.
  Routes stay thin. Policy, budget, model call, and tool binding
  sit in one harness path over the existing graph and RAG service.

EVALS PROVE GRADES:
  Do not claim security B+, cost B+, or orchestration A-
  until 9H.6 fixture themes pass.
  Live LLM keys are not required for pull-request CI.

ONE SUBSTEP:
  Implement only the substep in the prompt. Later 9H phases
  are not prerequisites and are not in scope for this session.
```
