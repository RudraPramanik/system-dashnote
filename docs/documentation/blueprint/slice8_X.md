# Slice 8X — Deploy-First Ship Path
## Detail index (CI → finish prod → frontend → evals → HITL)

> **Operator default:** Follow [`../blueprint8.md`](../blueprint8.md) first (Alive law + Tier 0/1/2). **This file is the Slice 8X detail index** for Composer phase IDs and links — not a second competing default.  
> **When to run:** After Slices **0–7.5** and platform **7P.0–7P.3** are complete.  
> **Goal (chosen):** Public production demo sooner — thin CI, finish VPS CD, minimum frontend, then golden evals (prefer live `--base-url`), then HITL on `/ai/agent*`.  
> **Not Slice 8 / 9:** Slice **8** = optional GraphRAG. Slice **9** = multi-agent (later). **8X** is the parallel ship path.  
> **Detail blueprints:** one Composer session ≈ one substep inside these files. Phase IDs (8X.1–8X.5) name the work packages; **calendar order** follows the locked sequence below (IDs are not chronological).

| Phase ID | Work package | Detail blueprint | Calendar position (chosen) |
|----------|--------------|------------------|----------------------------|
| **8X.1** | Thin CI | [`slice8_ci.md`](slice8_ci.md) | 1st |
| **8X.4** | Finish platform | [`slice-platform.md`](slice-platform.md) §7P.4–7P.6, 7P.8 | 2nd |
| **8X.5** | Frontend | [`frontendguide.md`](../frontendguide.md) · [`goal.md`](goal.md) §B | 3rd |
| **8X.2** | Eval harness | [`slice8_eval.md`](slice8_eval.md) | 4th (after 7P.8) |
| **8X.3** | HITL API-first | [`slice8_hitl.md`](slice8_hitl.md) | 5th |

**Also:** [`../blueprint8.md`](../blueprint8.md) (operator default) · [`production.md`](../production.md) · [`goal.md`](goal.md) · [`ai.md`](../ai.md)

---

## Slice Overview

```
Phase A — Seatbelt
  8X.1  Thin CI (7P.7)     → slice8_ci.md     (8X.1.0 → 8X.1.3)

Phase B — Highway (live URL)
  8X.4  Finish platform    → slice-platform.md (7P.4 → 7P.5 → 7P.6 → 7P.8)

Phase C — Show
  8X.5  Frontend pointer   → frontendguide.md + goal.md B-gate

Phase D — Measure & raise autonomy (after VPS smoke)
  8X.2  Eval harness       → slice8_eval.md   (8X.2.0 → 8X.2.4)
  8X.3  HITL API-first     → slice8_hitl.md   (8X.3.1 → 8X.3.4)
```

**Order is locked (chosen / deploy-first):** CI → finish prod → frontend → evals → HITL.  
Do **not** treat later calendar phases as prerequisites of earlier ones.  
Do **not** start **8X.2** immediately after **8X.1** on the chosen path — finish **8X.4** (and usually **8X.5**) first.  
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
**After CI:** continue with **8X.4** (remaining 7P.4–7P.6, 7P.8) — **not** 8X.2 evals.

---

## Path divergence (chosen vs alternate)

**Chosen (deploy-first):** CI → finish 7P.4–7P.8 → min frontend → evals → HITL.  
**Alternate (AI-depth-first):** CI → evals → HITL → finish prod → frontend — use only when harness depth matters more than a public URL this week.

`goal.md` mirrors these labels. Prefer **deploy-first** unless you explicitly switch to AI-depth-first.

---

## ARCHITECTURE LAW — Slice 8X (global)
### Paste before any 8X work; then paste the detail-file law for that substep

```
ARCHITECTURE LAW — DashNoteSystem Slice 8X (deploy-first: CI → finish prod → frontend → evals → HITL).

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

GATE EXCEPTION (chosen / deploy-first):
  Allowed BEFORE 7P.8: 7P.7 / 8X.1 Thin CI only (as harness work).
  Deferred UNTIL AFTER 7P.8 on chosen path: eval harness (8X.2), HITL on /ai/agent* (8X.3).
  Still BLOCKED until 7P.8: GraphRAG (Slice 8), multi-agent productization (Slice 9),
  new product domains, “we’re live in prod” portfolio claims.

DETAIL FILES (phase IDs; calendar order in slice overview):
  8X.1 → slice8_ci.md | 8X.4 → slice-platform.md | 8X.5 → frontendguide.md
  8X.2 → slice8_eval.md | 8X.3 → slice8_hitl.md
  One substep per Composer session.
```

---

## Pre-7P.8 exception — allowed vs blocked (chosen path)

| Allowed before 7P.8 | Deferred until after 7P.8 (chosen) | Blocked until 7P.8 passes |
|---------------------|------------------------------------|---------------------------|
| **8X.1** Thin CI ([`slice8_ci.md`](slice8_ci.md)) | **8X.2** Evals ([`slice8_eval.md`](slice8_eval.md)) | Slice **8** GraphRAG / Neo4j |
| Local compose iteration | **8X.3** HITL API ([`slice8_hitl.md`](slice8_hitl.md)) | Slice **9** multi-agent as product default |
| | **8X.5** Frontend (after smoke; usually before evals) | New product domains unrelated to harness |
| | | Claiming live production URL without smoke |

On the **alternate** AI-depth-first path, evals and HITL may run before 7P.8 — see path divergence.

---

## Phase summaries (full prompts in detail files)

### 8X.1 — Thin CI (7P.7) — calendar 1st

Seatbelt: inventory (Dockerfile Python/apt parity) → workflow skeleton → pytest green → docker build.  
**Full prompts:** [`slice8_ci.md`](slice8_ci.md)  
**Tracker:** `production.md` 7P.7 when done.  
**Next on chosen path:** 8X.4 (not 8X.2).

### 8X.4 — Finish platform — calendar 2nd

Execute in order from [`slice-platform.md`](slice-platform.md): **7P.4 → 7P.5 → 7P.6 → 7P.8**.  
Skip re-doing **7P.7** if 8X.1 is done. Do not duplicate platform prompts here.

```
ROLE: Senior platform engineer.
OBJECTIVE: Slice 8X.4 — Finish 7P.4–7P.6 and 7P.8 after 8X.1 (deploy-first).
Paste global Slice 8X law + Platform 7P law from slice-platform.md / deploy-low.md.
Use each sub-step OBJECTIVE block in slice-platform.md.
GATE: smoke exits 0 on prod; CD fails if smoke fails; local compose intact.
```

### 8X.5 — Frontend pointer — calendar 3rd

**Guides:** [`frontendguide.md`](../frontendguide.md) · [`goal.md`](goal.md) §B (B1–B7).  
HITL approval UX only after **8X.3** API exists (later). OpenAPI wins — do not invent backend routes.

```
ROLE: Senior Next.js engineer.
OBJECTIVE: Slice 8X.5 — B-gate frontend after 7P.8; optional HITL UX after 8X.3.
Paste frontend laws from frontendguide.md. Keep chat≠agent and citations-from-metadata.
GATE: Demo path works per goal.md (register → note → file → RAG → agent / HITL).
```

### 8X.2 — Eval harness — calendar 4th (after 7P.8)

Prefer first goldens against live/prod `--base-url`. Schema (fixture|live, trajectory fields, seed/fixture IDs) → retrieval/tenant goldens → runner → ≥5 agent trajectories (forbid surprise create) → optional fixture-only CI wire + honest pass rate.  
**Full prompts:** [`slice8_eval.md`](slice8_eval.md)  
**Sequence:** Follow chosen order in this index — start after 7P.8 on deploy-first.

### 8X.3 — HITL API-first — calendar 5th

Interrupt (version-grounded) → locked SSE `approval_required` (emit-then-close) → resume/reject with workspace ownership check → script/tests. **FE out of gate.** Checkpointer holds pending state.  
**Full prompts:** [`slice8_hitl.md`](slice8_hitl.md)  
**Sequence:** Follow chosen order in this index — after evals on deploy-first.

---

## Fallback / out-of-scope (path-level)

| Do NOT require for 8X baseline | Where it lives instead |
|--------------------------------|------------------------|
| Single mega-prompt for all CI+evals+HITL | Split detail blueprints |
| Polished HITL FE in 8X.3 | 8X.5 |
| Live LLM required for PR CI | Never — see `slice8_ci.md` / `slice8_eval.md` |
| Multi-agent supervisor | Slice 9 |
| Forked copy of 7P.4–7P.8 prompts | `slice-platform.md` |
| Dropping job-search evals forever | C-gate in `goal.md` — deferred, not optional |

---

## Implementation status tracker

```
Calendar (chosen):
  8X.1 Thin CI          [ ]  → slice8_ci.md
  8X.4 Finish 7P.4–8    [ ]  → slice-platform.md
  8X.5 Frontend B-gate  [ ]  → frontendguide.md
  8X.2 Eval harness     [ ]  → slice8_eval.md
  8X.3 HITL API         [ ]  → slice8_hitl.md
```

---

## What this index does NOT authorize

- Rewriting completed slices 0–7.5  
- Skipping tenant RBAC or soft-dep laws for demo speed  
- Shipping multi-agent fashion without evals + HITL (when those phases are due)  
- Marking portfolio “production live” before 7P.8 smoke  
- Skipping C-gate evals permanently because they are sequenced after VPS  

**Start:** [`slice8_ci.md`](slice8_ci.md) → substep **8X.1.0 Inventory** → then **8X.4**.
