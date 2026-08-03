# Slice 8X — CI → Evals → HITL → Finish Prod
## Ship-path index (AI-engineer track)

> **When to run:** After Slices **0–7.5** and platform **7P.0–7P.3** are complete.  
> **Goal:** Harden the AI harness **before** finishing VPS CD — thin CI, golden evals, HITL on `/ai/agent*`, then remaining 7P, then frontend.  
> **Not Slice 8 / 9:** Slice **8** = optional GraphRAG. Slice **9** = multi-agent (later). **8X** is the parallel ship path.  
> **Detail blueprints (option B):** one Composer session ≈ one substep inside these files.

| Phase | Detail blueprint |
|-------|------------------|
| **8X.1** Thin CI | [`slice8_ci.md`](slice8_ci.md) |
| **8X.2** Eval harness | [`slice8_eval.md`](slice8_eval.md) |
| **8X.3** HITL API-first | [`slice8_hitl.md`](slice8_hitl.md) |
| **8X.4** Finish platform | [`slice-platform.md`](slice-platform.md) §7P.4–7P.6, 7P.8 |
| **8X.5** Frontend | [`frontendguide.md`](../frontendguide.md) · [`goal.md`](goal.md) §B |

**Also:** [`production.md`](../production.md) · [`goal.md`](goal.md) · [`ai.md`](../ai.md)

---

## Slice Overview

```
Phase A — Seatbelt
  8X.1  Thin CI (7P.7)     → slice8_ci.md     (8X.1.0 → 8X.1.3)

Phase B — Measure & raise autonomy (before full VPS CD)
  8X.2  Eval harness       → slice8_eval.md   (8X.2.0 → 8X.2.4)
  8X.3  HITL API-first     → slice8_hitl.md   (8X.3.1 → 8X.3.4)

Phase C — Highway
  8X.4  Finish platform    → slice-platform.md (7P.4 → 7P.5 → 7P.6 → 7P.8)

Phase D — Show
  8X.5  Frontend pointer   → frontendguide.md + goal.md B-gate
```

**Order is locked:** CI → evals → HITL API → finish prod → frontend.  
Do **not** treat later phases as prerequisites of earlier ones.  
Do **not** paste a single mega-prompt for all of 8X.1–8X.3 — use the detail files’ substages.

---

## Readiness gate (before 8X.1)

| Prerequisite | Expected state | Action if missing |
|--------------|----------------|-------------------|
| Slices 0–7.5 | Local RAG + agent + automation work | Finish earlier slice blueprints |
| 7P.0–7P.3 | Env contract, `docker-compose.prod.yml`, soft Qdrant boot | See `slice-platform.md` / `production.md` |
| Local health | `curl http://127.0.0.1/health` → 200 | Fix api/db/redis |
| Tests | Local pytest baseline understood | Start with `slice8_ci.md` §8X.1.0 inventory |
| `.env` not committed | `.env` in `.gitignore` | Verify |
| Live prod claim | **None yet** | Do not claim production-live until 7P.8 smoke passes |

**Verdict:** Open [`slice8_ci.md`](slice8_ci.md) and start **8X.1.0**.

---

## Path divergence (vs `goal.md` short-order)

`goal.md` still documents an alternate **fastest live URL** order.  
**Slice 8X is the chosen AI-engineer path.** Prefer 8X unless you need a public URL this week above harness depth.

---

## ARCHITECTURE LAW — Slice 8X (global)
### Paste before any 8X work; then paste the detail-file law for that substep

```
ARCHITECTURE LAW — DashNoteSystem Slice 8X (CI → evals → HITL → finish prod).

CRITICAL — DO NOT BREAK LOCAL DEV:
  docker-compose.yml remains the FULL local stack (db, redis, qdrant, api, worker, nginx, prometheus).

CHAT ≠ AGENT:
  Keep POST /ai/chat* and POST /ai/agent* as separate surfaces.

TENANCY:
  workspace_id / user_id / role from JWT → RequestContext / trusted graph state only.

CI LAW:
  PR CI: pytest + docker build only. No prod VPS secrets, no SSH, no required live LLM keys.

PROD CLAIMS:
  Do not claim “production live” until 7P.8 smoke exits 0.

GATE EXCEPTION (intentional):
  Allowed BEFORE 7P.8: 7P.7 CI, eval harness, HITL on existing /ai/agent*.
  Still BLOCKED until 7P.8: GraphRAG (Slice 8), multi-agent productization (Slice 9),
  new product domains, “we’re live in prod” portfolio claims.

DETAIL FILES:
  8X.1 → slice8_ci.md | 8X.2 → slice8_eval.md | 8X.3 → slice8_hitl.md
  One substep per Composer session.
```

---

## Pre-7P.8 exception — allowed vs blocked

| Allowed before 7P.8 | Blocked until 7P.8 passes |
|---------------------|---------------------------|
| **8X.1** Thin CI ([`slice8_ci.md`](slice8_ci.md)) | Slice **8** GraphRAG / Neo4j |
| **8X.2** Evals ([`slice8_eval.md`](slice8_eval.md)) | Slice **9** multi-agent as product default |
| **8X.3** HITL API ([`slice8_hitl.md`](slice8_hitl.md)) | New product domains unrelated to harness |
| Local compose iteration | Claiming live production URL without smoke |

---

## Phase summaries (full prompts in detail files)

### 8X.1 — Thin CI (7P.7)

Seatbelt: inventory → workflow skeleton → pytest green → docker build.  
**Full prompts:** [`slice8_ci.md`](slice8_ci.md)  
**Tracker:** `production.md` 7P.7 when done.

### 8X.2 — Eval harness

Schema → retrieval/tenant goldens → runner → ≥5 agent trajectories (forbid surprise create) → optional CI wire + honest pass rate.  
**Full prompts:** [`slice8_eval.md`](slice8_eval.md)

### 8X.3 — HITL API-first

Interrupt → SSE `approval_required` → resume/reject → script/tests. **FE out of gate.**  
**Full prompts:** [`slice8_hitl.md`](slice8_hitl.md)

### 8X.4 — Finish platform

Execute in order from [`slice-platform.md`](slice-platform.md): **7P.4 → 7P.5 → 7P.6 → 7P.8**.  
Skip re-doing **7P.7** if 8X.1 is done. Do not duplicate platform prompts here.

```
ROLE: Senior platform engineer.
OBJECTIVE: Slice 8X.4 — Finish 7P.4–7P.6 and 7P.8 after 8X.1–8X.3.
Paste global Slice 8X law + Platform 7P law from slice-platform.md / deploy-low.md.
Use each sub-step OBJECTIVE block in slice-platform.md.
GATE: smoke exits 0 on prod; CD fails if smoke fails; local compose intact.
```

### 8X.5 — Frontend pointer

**Guides:** [`frontendguide.md`](../frontendguide.md) · [`goal.md`](goal.md) §B (B1–B7).  
HITL approval UX only after **8X.3** API exists. OpenAPI wins — do not invent backend routes.

```
ROLE: Senior Next.js engineer.
OBJECTIVE: Slice 8X.5 — B-gate frontend; optional HITL UX after 8X.3.
Paste frontend laws from frontendguide.md. Keep chat≠agent and citations-from-metadata.
GATE: Demo path works per goal.md (register → note → file → RAG → agent / HITL).
```

---

## Fallback / out-of-scope (path-level)

| Do NOT require for 8X baseline | Where it lives instead |
|--------------------------------|------------------------|
| Single mega-prompt for all CI+evals+HITL | Split detail blueprints |
| Polished HITL FE in 8X.3 | 8X.5 |
| Live LLM required for PR CI | Never — see `slice8_ci.md` / `slice8_eval.md` |
| Multi-agent supervisor | Slice 9 |
| Forked copy of 7P.4–7P.8 prompts | `slice-platform.md` |

---

## Implementation status tracker

```
8X.1 Thin CI          [ ]  → slice8_ci.md
8X.2 Eval harness     [ ]  → slice8_eval.md
8X.3 HITL API         [ ]  → slice8_hitl.md
8X.4 Finish 7P.4–8    [ ]  → slice-platform.md
8X.5 Frontend B-gate  [ ]  → frontendguide.md
```

---

## What this index does NOT authorize

- Rewriting completed slices 0–7.5  
- Skipping tenant RBAC or soft-dep laws for demo speed  
- Shipping multi-agent fashion without evals + HITL  
- Marking portfolio “production live” before 7P.8 smoke  

**Start:** [`slice8_ci.md`](slice8_ci.md) → substep **8X.1.0 Inventory**.
