## Context

Slices 0–7.5 and platform 7P.0–7P.3 are complete. Thin CI, evals, HITL, remaining 7P, and frontend are not started. Planning currently locks **CI → evals → HITL → finish prod → frontend** as the chosen AI-engineer path (`slice8_X.md`, `goal.md` preferred order), with a documented alternate “fastest live URL” that puts evals after a public API.

The operator chose the alternate: **public VPS first**, evals as the next milestone after deploy (not dropped). Docs and path specs must flip which order is “chosen” vs “alternate” so the next `/opsx:apply` or Composer session does not start 8X.2 immediately after CI.

Detail blueprints (`slice8_ci.md`, `slice8_eval.md`, `slice8_hitl.md`) remain valid implementation guides; only **sequencing and gate narrative** in the path index and cross-links change.

## Goals / Non-Goals

**Goals:**

- Make deploy-first the **active** Slice 8X operator order in path TOC + blueprint specs and canonical cross-links.
- Keep thin CI (8X.1) as the first implementation step (cheap seatbelt before VPS).
- Keep evals and HITL as explicit later milestones (job-search C-gate still requires evals; HITL remains valuable but post-URL).
- Preserve GraphRAG (Slice 8) / multi-agent (Slice 9) block until 7P.8 smoke passes.
- Preserve “do not claim production-live without 7P.8 smoke.”

**Non-Goals:**

- Implementing CI workflows, deploy scripts, smoke, evals/, HITL, or frontend.
- Rewriting the full Composer task bodies inside `slice8_ci.md` / `slice8_eval.md` / `slice8_hitl.md` (only path-order callouts if a sentence claims they must run before 7P.8 as the preferred spine).
- Changing `production-platform` behavioral requirements (R2, smoke, CI/CD mechanics).
- Abandoning evals permanently or moving them out of the job-search gate.

## Decisions

### Decision: Deploy-first is chosen; AI-depth-first becomes alternate

| Order | Role after this change |
|-------|------------------------|
| CI → finish 7P.4–7P.8 → min frontend → evals → HITL | **Chosen** (operator default) |
| CI → evals → HITL → finish prod → frontend | **Alternate** (AI-depth / harness-before-URL) |

**Why:** Matches operator priority (live demo soon) and already existed as `goal.md` “fastest live URL.” Flipping labels avoids dual “preferred” contradictions.

**Alternative considered:** Keep 8X order and only note a temporary pause — rejected; operators would still follow the bold “order is locked” line into evals before VPS.

### Decision: Thin CI still precedes VPS

8X.1 remains first. PR pytest + docker build has no prod secrets and reduces broken deploys. Skipping CI entirely was rejected as a false optimization.

### Decision: Pre-7P.8 exception narrows

| Before (depth-first) | After (deploy-first) |
|----------------------|----------------------|
| Allowed before 7P.8: CI, evals, HITL on `/ai/agent*` | Allowed before 7P.8: **CI (and only CI as harness work)** |
| Evals/HITL encouraged before CD | Evals/HITL **deferred until after** 7P.8 smoke (then frontend, then evals, then HITL) |

GraphRAG / multi-agent / new domains remain blocked until 7P.8 regardless.

**Why:** Aligns gate tables with chosen path. Detail files for 8X.2/8X.3 stay in-repo for when those phases start.

### Decision: Evals prefer live `--base-url` after deploy

Document that the first eval milestone SHOULD target the production (or staging) API URL so corpus IDs and tenant cases hit real infra. Fixture/CI-gated evals remain Phase 2 polish (already in ship-plan).

**Alternative considered:** Build fixture-mode evals before VPS anyway — useful, but conflicts with “evals after VPS” and can wait.

### Decision: Docs-only change; next code change is separate

This change edits planning artifacts only. Immediate follow-up implementation (separate change or apply session): **8X.1.0 inventory → CI**, then **7P.4–7P.8**.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Job search starts with live URL but empty eval story | Keep C1–C4 in `goal.md` gate; state evals as next milestone after deploy/UI, not optional forever |
| Detail blueprints still say “after Slice 7” / encourage pre-7P.8 evals | Path index is source of order; add one-line “sequence per `slice8_X.md` chosen path” where those files claim preferred pre-7P.8 ordering |
| Spec sync leaves main `openspec/specs` stale until archive | Sync deltas when archiving this change (or `/opsx:sync`) |
| Skipping HITL until late leaves mutation autonomy ungoverned in demos | Prefer demo paths that use chat/search first; HITL remains next after evals |

## Migration Plan

1. Land this change’s doc + delta-spec edits.
2. Archive/sync so main path specs match deploy-first.
3. Start implementation at `slice8_ci.md` §8X.1.0 (new change or apply session — not this change’s tasks beyond docs).
4. Rollback: restore previous “chosen = depth-first” wording in the same files if the operator reverts priority.

## Open Questions

- None blocking this docs change. Frontend repo location (same monorepo vs separate) is out of scope until 8X.5.
- Whether HITL stays after evals or can slip after min UI before evals: default **after evals** unless operator revisits.
