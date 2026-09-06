## Context

See `proposal.md` for why. Today: Slice 8X detail blueprints under `docs/documentation/blueprint/` plus `goal.md` / `ship-plan.md` already describe deploy-first → evals → HITL, but operators lack one locked “Alive + job gate + Tier 1/2” document. `docs/documentation/blueprint8.md` is empty. Platform 7P.0–7P.8 is marked done in `production.md` (live VPS proof still required to claim production-live). Frontend lives in sibling `dashnotes/`. This change is **documentation lock only**—no app code.

## Goals / Non-Goals

**Goals:**

- Make `blueprint8.md` the operator-default path (Alive law, Tier 0/1/2, GraphRAG intro, links to detail blueprints).
- Lock `ship-plan.md` to that path; refresh stale Day-0 claims that contradict current repo state where cheap and honest.
- Cross-link `goal.md`, `production.md`, `total.md`, `slice8_X.md` so blueprint8 leads without deleting Slice 8X detail prompts.
- Record eval stack decision: Langfuse-native primary; RAGAS optional nightly; DeepEval not required.

**Non-Goals:**

- Implementing `evals/`, HITL interrupt code, Langfuse span payload changes, hybrid search, or GraphRAG/Neo4j.
- Changing API routes or chat≠agent laws.
- Replacing `slice8_eval.md` / `slice8_hitl.md` Composer prompts—only re-parent under blueprint8.

## Decisions

### D1 — blueprint8 leads; `blueprint/` stays executable
**Choice:** Operators open `blueprint8.md` first; detail work still uses `slice8_X.md`, `slice8_eval.md`, `slice8_hitl.md`, `slice8_ci.md`, `frontendguide.md`.  
**Why:** Avoid rewriting all Composer prompts; avoid two competing “defaults.”  
**Alt:** Merge everything into blueprint8 only → too long, orphans existing OpenSpec blueprint specs.

### D2 — This apply is docs-only; code deepeners stay sequenced
**Choice:** Apply writes docs + pointers. Tier 1/2 product work (HITL, Langfuse enrichment, harness) remains future applies guided by detail blueprints.  
**Why:** Matches propose/apply boundary and keeps Alive demo unblocked.  
**Alt:** Bundle HITL+evals implementation → scope explosion.

### D3 — Eval stack: Langfuse-native (A), optional RAGAS (B later)
**Choice:** Document Langfuse datasets/experiments/judges as primary thickener after C-gate; custom `evals/` remains C-gate; RAGAS optional nightly; DeepEval not in default path.  
**Why:** Langfuse already wired via `observability.tracing`; avoids dual platforms.  
**Alt:** DeepEval as CI → overlaps custom runner; RAGAS-only → weaker agent/HITL story.

### D4 — GraphRAG = short intro, not a slice to ship
**Choice:** ~½–1 page in blueprint8: what / why people use it / why deferred / pointer to Slice 8 in `total.md`.  
**Why:** User asked for introduction without VPS productization.  
**Alt:** Full GraphRAG blueprint → contradicts Alive/VPS constraint.

### D5 — blueprint8 outline (content contract for apply)
Apply MUST fill `blueprint8.md` with at least:

1. Purpose + “follow this first” + links to `blueprint/` details  
2. Alive law (API/FE/AI shippable; VPS vs local split)  
3. Tier 0 job gate (A/B/C/D aligned with `goal.md`)  
4. Tier 1 deepeners (HITL, Langfuse depth, cost/latency, fixture CI, agent goldens, failure modes)  
5. Tier 2 lab (recall@k/MRR, faithfulness nightly, EXPERIMENTS.md, optional hybrid/rerank)  
6. Eval → improve → gate loop diagram  
7. GraphRAG short intro + non-goals  
8. Sequence diagram: spine vs thicken (compatible with Slice 8X deploy-first)  
9. Explicit non-goals (multi-agent supervisor, Neo4j on VPS, live judges in PR CI)

### D6 — ship-plan edits
**Choice:** Add a top “Locked path” callout → blueprint8; align Phase 2 checklist with Tier 1/2; lightly correct Day-0 table where CI/workflows already exist (honest, not a full rewrite).  
**Why:** User asked to lock ship-plan without discarding day-by-day usefulness.

## Risks / Trade-offs

- [Two defaults confuse operators] → Mitigation: every touched tracker points to blueprint8 first; slice8_X labeled “detail index.”
- [Ship-plan Day-0 still stale in places] → Mitigation: fix only clear falsehoods (CI present); leave day numbers; note “see production.md for 7P status.”
- [Readers think GraphRAG is next] → Mitigation: bold deferral + non-goals in same section.
- [Specs mention eval thickeners before harness exists] → Mitigation: thickeners are documentation requirements now; implementation deferred explicitly in tasks.

## Migration Plan

1. Write `blueprint8.md` per D5.  
2. Update `ship-plan.md` lock + Phase 2 alignment.  
3. Add short pointers in `goal.md`, `production.md`, `total.md`, `slice8_X.md` (and `slice-platform.md` if a one-liner fits).  
4. No runtime deploy; rollback = revert doc commits.

## Open Questions

None that block docs apply. (Later product applies will decide exact Langfuse span fields and HITL SSE shape using existing `slice8_hitl.md` locks.)
