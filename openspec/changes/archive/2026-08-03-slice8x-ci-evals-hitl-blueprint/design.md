## Context

DashNoteSystem has completed AI vertical slices **0–7.5** and platform substages **7P.0–7P.3** (env contract, prod compose, soft Qdrant boot). Remaining 7P work (R2, deploy scripts, smoke, CI, CD), job-search evals (`ai-eval-harness`), frontend, and agent HITL are still open.

Explore decisions locked an **AI-engineer-optimized order**: thin CI → evals (including agent trajectories) → HITL API on `/ai/agent*` → finish prod (7P.4–7P.8) → frontend. That order amends the strict `slice-platform.md` rule “no feature slices before 7P.8” for **harness hardening only**.

Today that plan lives in chat plus scattered docs (`goal.md`, `production.md`, `slice-platform.md`, `total.md`). `docs/documentation/blueprint/slice8_X.md` is empty and is the intended single executable blueprint (same style as `slice-platform.md`: laws, substages, Cursor prompts, gates).

This change authors that blueprint and cross-links — **no runtime code**.

## Goals / Non-Goals

**Goals:**

- One Cursor-ready blueprint at `slice8_X.md` with phases, substages, paste-first architecture laws, per-step prompts, validation gates, and fallback boundaries.
- Explicit sequencing: **8X.1 CI → 8X.2 evals → 8X.3 HITL API → 8X.4 finish 7P.4–7P.8 → 8X.5 frontend pointer** (frontend detail stays in `frontendguide.md` / B-gate).
- Document the intentional pre-7P.8 exception: CI + evals + HITL-on-existing-agent allowed; Slice 8 GraphRAG / Slice 9 multi-agent / new product domains still blocked until 7P.8.
- Cross-link so operators discover 8X from `goal.md`, `production.md`, `total.md`, and `slice-platform.md`.

**Non-Goals:**

- Implementing `.github/workflows/ci.yml`, `evals/`, HITL interrupt/resume code, R2, CD, or Next.js in this change.
- Replacing or rewriting completed blueprints (`slice1`–`slice7`, `slice-platform` body).
- Multi-agent supervisor, GraphRAG, hybrid rerank, or automation approval queue as required 8X baseline work.
- Changing OpenAPI contracts in this change (HITL contract is described for a **later** implement change).

## Decisions

### D1 — Blueprint ID: Slice 8X (not Slice 8 / 9)

- **Choice:** Name the path **Slice 8X** in `slice8_X.md` — a parallel “ship path” between completed 7.5 and optional Slice 8/9.
- **Why:** `total.md` already reserves Slice 8 = GraphRAG and Slice 9 = multi-agent. Overloading those numbers would confuse deferred work with the job-search path.
- **Alternatives:** Call it “Phase J” or extend 7P only — rejected; 7P is platform-only and goal.md already mixes A/B/C/D gates that need one orchestration doc.

### D2 — Match `slice-platform.md` document shape

- **Choice:** Structure 8X like platform: overview ASCII phases → readiness gate → ARCHITECTURE LAW block → numbered substages each with Goal / Laws / OBJECTIVE prompt / Gate / Commit hint → fallback table → “what not to touch.”
- **Why:** Operators and agents already know that pattern; copy-paste Composer sessions work the same way.
- **Alternatives:** Free-form ship-plan prose only — weaker for step-gated implementation.

### D3 — Phase order (locked)

```
8X.1  Thin CI (7P.7)           pytest + docker build; no prod secrets
8X.2  Eval harness             golden retrieval + tenant + ≥5 agent trajectories
8X.3  HITL API-first           interrupt before create/update; resume by thread_id
8X.4  Finish platform          7P.4 → 7P.5 → 7P.6 → 7P.8 (reuse slice-platform prompts)
8X.5  Frontend pointer         B-gate via frontendguide.md (out of deep detail here)
```

- **Why:** Seatbelt (CI) before intelligence measurement (evals) before raising autonomy (HITL) before highway (prod CD). Aligns with AI-engineer portfolio narrative.
- **Alternatives:** `goal.md` “prod first” order — still valid for fastest live URL; 8X deliberately front-loads AI proof. Document both: 8X is the chosen path; note divergence from goal.md short-order.

### D4 — Gate exception language

- **Choice:** Blueprint MUST state allowed-before-7P.8 vs still-blocked lists.
- **Allowed:** 7P.7 CI; eval corpus/runner; HITL on existing `/ai/agent*` (harness raise, not new domain).
- **Still blocked:** GraphRAG, multi-agent/supervisor-as-default, new product modules, claiming “production live” without 7P.8 smoke.
- **Why:** Preserves platform spirit while unblocking career-critical harness work on local compose.

### D5 — Evals: deterministic CI vs live optional

- **Choice:** Blueprint instructs PR CI to run unit/module pytest (+ later deterministic/fixture agent cases). Live LLM eval against a URL is operator/nightly — not required to green PR CI (matches `production-platform` “no live LLM secrets for CI”).
- **Why:** Flaky paid LLM calls in PR CI destroy trust.
- **Alternatives:** Always-live eval in CI — rejected for cost/flakes.

### D6 — HITL scope in blueprint

- **Choice:** 8X.3 specifies **API + SSE contract + script/curl smoke** only. Approval UI is 8X.5 / B5 follow-on.
- **Why:** Avoid FE calendar eating the AI-eng wedge; checkpointer resume must be proven on local Postgres first.
- **Alternatives:** Full Next HITL before prod — deferred by path decision.

### D7 — Cross-links, not duplication of 7P.4–7P.8 prompts

- **Choice:** 8X.4 points at `slice-platform.md` substages 7P.4–7P.8 for detailed prompts; 8X only orders them after 8X.1–8X.3 and updates tracker language in `production.md`.
- **Why:** Single source of truth for deploy mechanics; avoid drift between two full prompt copies.

### D8 — This OpenSpec change vs later implement changes

- **Choice:** Apply of *this* change writes the blueprint + doc pointers only. Separate future changes/implement sessions execute 8X.1, 8X.2, etc.
- **Why:** Keeps proposal scope honest and reviewable.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators ignore 8X and follow old “prod first” in goal.md | Cross-link + short “path divergence” callout in both docs |
| HITL scope creeps into polished FE before CD | Fallback boundary: API-first gate; FE listed after 8X.4 |
| Blueprint becomes a second conflicting 7P law | Explicit exception list; CD/smoke still required before “live prod” claims |
| Agent trajectory evals underspecified | Blueprint lists minimum scenarios (search-only, create-when-asked, forbid surprise create, update-when-asked, limit/stop) |
| Empty file left unfinished | tasks.md gate: file non-empty with all substages + laws + fallbacks |

## Migration Plan

1. Author `slice8_X.md` from design + specs.
2. Add “Slice 8X” pointers in `total.md` overview, `goal.md` recommended order note, `production.md` tracker note, `slice-platform.md` gate exception one-liner.
3. No runtime deploy; rollback = revert doc commits.

## Open Questions

- Exact HITL SSE event name (`approval_required` vs existing stream event taxonomy) — blueprint proposes `approval_required`; implement change confirms against `ai_routes/agent.py` stream events.
- Whether agent goldens live under `evals/golden/agent_tools.jsonl` (preferred in artifacts) vs `tests/ai/` only — blueprint prefers `evals/golden/` + runner extension to match `ai-eval-harness`.
- Filename casing `slice8_X.md` vs `slice8x.md` — keep user’s `slice8_X.md`.
