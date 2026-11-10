# Blueprint 9 — Harness Hardening (operator default for this path)

> **Follow this document first** when hardening the AI harness.  
> **Blueprint 8 stays the ship and hire default.** This file does not replace Tier 0, the Alive law, or chat-versus-agent coexistence.  
> **Detail / Composer prompts:** [`blueprint/slice9_H.md`](blueprint/slice9_H.md) is the only phase-order source. One Composer session ≈ one substep.  
> **Not Slice 9.** Phase IDs are **9H.***. Multi-agent supervisor productization stays reserved as Slice 9 in [`blueprint/total.md`](blueprint/total.md). GraphRAG Slice 8 is also out of this path.

| Need | Open |
|------|------|
| Phase index + global law | [`blueprint/slice9_H.md`](blueprint/slice9_H.md) |
| 9H.1 tenant bind | [`blueprint/slice9_trust.md`](blueprint/slice9_trust.md) |
| 9H.2 ACL + 9H.3 injection | [`blueprint/slice9_policy.md`](blueprint/slice9_policy.md) |
| 9H.4 AI budgets | [`blueprint/slice9_cost.md`](blueprint/slice9_cost.md) |
| 9H.5 degrade + control plane | [`blueprint/slice9_resilience.md`](blueprint/slice9_resilience.md) |
| 9H.6 goldens that prove grades | [`blueprint/slice9_eval.md`](blueprint/slice9_eval.md) |
| Ship / hire path (unchanged) | [`blueprint8.md`](blueprint8.md) |

**This file is planning.** Applying Blueprint 9 writes these documents. Runtime harness code is a later change per substep. Do not claim security B+, cost B+, or orchestration A- until the 9H.6 fixture themes pass.

---

## Alive law

The product stays demoable while the harness hardens.

| Alive means | Does not mean |
|-------------|---------------|
| Local `docker compose` full stack keeps working (`docker-compose.yml`: db, redis, qdrant, api, worker, nginx, prometheus) | Rewriting compose or dropping a service to “simplify” the harness |
| `/ai/chat*` and `/ai/agent*` **both** remain | Replacing chat with the agent |
| HITL still blocks create/update until a human approves | Removing approval to make tools “faster” |
| VPS demo stays on the current thin box | Putting live red-team judges or GPU models on the VPS |

| Runs on the product path | Fixture, local, or nightly only |
|--------------------------|----------------------------------|
| Trust bind, tool ACL, delimiters, Redis budgets, degrade modes | Live jailbreak suites and LLM-as-judge |
| Fixture goldens in PR CI (no live model key) | Operator red-team against production models |

**9H.6.2 lane:** Harness fixture themes are on the merge-blocking thin CI pytest path (`tests/ai/test_harness_fixture_themes.py`; see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) and [`evals/README.md`](../../evals/README.md)). Live red-team / judges remain operator or nightly and non-blocking. Grade B+/A- wording waits for 9H.6.3.

---

## Grade targets

Honest targets for this notes workspace assistant, not a generic enterprise platform:

| Layer | From | Toward | What “done” means here |
|-------|------|--------|------------------------|
| Security | D+ | **B+** | Tenant and role are server-bound; retrieved text is data; mutations stay behind HITL; fixture attacks fail closed |
| Cost | C- | **B+** | Per-user and per-workspace AI ceilings with a controlled 429/SSE refusal; Redis errors fail open |
| Orchestration | B+ | **A-** | One control plane over the existing graph: policy, budget, model, tools; typed errors; documented degrade |

---

## Locked order

`slice9_H.md` wins if any detail file disagrees.

```
9H.1  Trust bind          slice9_trust.md       tenant from HarnessContext
9H.2  Tool ACL + errors   slice9_policy.md      note permissions + envelopes
9H.3  Injection hygiene   slice9_policy.md      delimiters; content is data
9H.4  AI budgets          slice9_cost.md        user/minute + workspace/day
9H.5  Degrade + plane     slice9_resilience.md  cooldown, fallback, thin routes
9H.6  Prove the grades    slice9_eval.md        fixture goldens, then claims
```

Later phases are **not** prerequisites of earlier ones. Do not start 9H.4 inside a 9H.1 session.

---

## HarnessContext

One trusted session object, built from the JWT request context (`user_id`, `workspace_id`, `role`) plus trace id and remaining budget. The graph stores it once per invoke. Tools read tenant fields only from it.

```
JWT request
    │
    ▼
HarnessContext  (workspace, user, role, trace, budget)
    │
    ├── policy / budget gate
    ▼
model call  (chat or agent; existing LiteLLM fallback stays)
    │
    ▼
tool wrapper  ── overwrites tenant from HarnessContext
    │
    ▼
NoteService / RagService
```

**Fail closed** on tenant and authorization mistakes: missing context or a forbidden role becomes a typed deny, never a cross-workspace call.  
**Fail open** only for AI budget checks when Redis errors: log a warning and allow the request, same idea as the global rate limiter. `/health` and `/health/ai` do not read AI budget keys.

Preferred tool schemas omit `workspace_id`, `user_id`, and `role`. Fallback if the framework requires those fields: overwrite them from HarnessContext before any service call and ignore the model values. Log when the model value differed.

---

## Non-goals

- Multi-agent supervisor (Slice 9 in `total.md`)
- GraphRAG / Neo4j on the small VPS (Slice 8)
- Replacing `/ai/chat*` with `/ai/agent*`
- A billing or payments product
- A second permission engine (OPA, Cedar, or a new role table)
- A third-party moderation vendor or a PII redaction pipeline as a B+ requirement
- Live model judges inside pull-request CI

---

## How to work

1. Read **this file** for targets and order.  
2. Paste the architecture law from [`slice9_H.md`](blueprint/slice9_H.md), then one substep prompt from the phase file.  
3. Keep the demo alive. Do not claim B+ or A- until [`slice9_eval.md`](blueprint/slice9_eval.md) themes pass.  
4. Ship path and hire gate stay on [`blueprint8.md`](blueprint8.md).
