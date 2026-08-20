## 1. Blueprint skeleton

- [x] 1.1 Draft `docs/documentation/blueprint/slice8_X.md` header: Slice 8X title, when-to-run, prerequisites (0–7.5 + 7P.0–7P.3 done), goal, and explicit distinction from Slice 8 GraphRAG / Slice 9 multi-agent
- [x] 1.2 Add phase overview ASCII/list: 8X.1 CI → 8X.2 evals → 8X.3 HITL API → 8X.4 finish 7P.4–7P.8 → 8X.5 frontend pointer
- [x] 1.3 Add readiness gate table (local health, pytest green, 7P.0–7P.3 complete, no claim of live prod yet)

## 2. Laws, gates, and fallbacks

- [x] 2.1 Write paste-first ARCHITECTURE LAW block for 8X (local compose sacred, chat≠agent, tenant from state not LLM, no prod secrets in CI, no live-prod claims before 7P.8 smoke)
- [x] 2.2 Document intentional pre-7P.8 exception: allowed (CI, evals, HITL on `/ai/agent*`) vs blocked (GraphRAG, multi-agent productization, new domains)
- [x] 2.3 Add fallback / out-of-scope table (no polished HITL FE in 8X.3, no live LLM required for PR CI, no Slice 9 supervisor-as-default, defer hybrid/rerank)

## 3. Substage prompts (Cursor-ready)

- [x] 3.1 Write 8X.1 Thin CI substage: goal, laws, OBJECTIVE prompt pointing at `slice-platform.md` 7P.7 patterns, gate (pytest + docker build, no prod secrets), commit hint
- [x] 3.2 Write 8X.2 Eval harness substage: retrieval + tenant isolation + ≥5 agent trajectories (include forbid surprise create), runner CLI, deterministic CI vs optional live eval, gate criteria
- [x] 3.3 Write 8X.3 HITL API-first substage: interrupt before create/update, SSE `approval_required` (or confirmed event name), resume by thread/checkpoint, curl/script gate — FE not required
- [x] 3.4 Write 8X.4 Finish platform substage: ordered pointer to 7P.4 → 7P.5 → 7P.6 → 7P.8 in `slice-platform.md` (do not duplicate full prompts; require smoke gate)
- [x] 3.5 Write 8X.5 Frontend pointer: B-gate + `frontendguide.md`; HITL approval UX only after 8X.3 API exists

## 4. Cross-links and tracker notes

- [x] 4.1 Add Slice 8X entry/pointer in `docs/documentation/blueprint/total.md` slice overview
- [x] 4.2 Update `docs/documentation/blueprint/goal.md` recommended-order note to reference Slice 8X path (and note divergence from old “prod first” short-order)
- [x] 4.3 Update `docs/documentation/production.md` with 8X sequencing note after 7P.0–7P.3 (CI/evals/HITL before finishing 7P.4–7P.8)
- [x] 4.4 Add one-liner gate-exception pointer in `docs/documentation/blueprint/slice-platform.md` to Slice 8X

## 5. Verify

- [x] 5.1 Skim `slice8_X.md` against `openspec/changes/slice8x-ci-evals-hitl-blueprint/specs/slice8x-path-blueprint/spec.md` — phases, laws, fallbacks, eval/HITL minima, cross-links all present
- [x] 5.2 Confirm this change adds no application code / no workflow YAML (docs-only gate)
