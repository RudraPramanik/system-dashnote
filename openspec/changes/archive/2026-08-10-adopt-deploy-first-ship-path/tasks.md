## 1. Path index (`slice8_X.md`)

- [x] 1.1 Rewrite Slice Overview / phase list to chosen order: 8X.1 CI → 8X.4 finish platform → 8X.5 frontend → 8X.2 evals → 8X.3 HITL
- [x] 1.2 Update “order is locked” and readiness verdict: after 7P.0–7P.3, start 8X.1.0 then remaining 7P (not 8X.2 next)
- [x] 1.3 Flip path-divergence: deploy-first = chosen; CI→evals→HITL→prod = alternate AI-depth-first
- [x] 1.4 Update architecture-law / pre-7P.8 exception table: CI allowed before 7P.8; evals/HITL deferred on chosen path; GraphRAG/Slice 9 still blocked
- [x] 1.5 Keep 8X.1–8X.3 links to detail blueprints; clarify phase numbers vs calendar order where confusing

## 2. Cross-link docs

- [x] 2.1 Update `goal.md` recommended order: preferred = deploy-first; former 8X preferred becomes alternate (or swap section titles accordingly)
- [x] 2.2 Update `production.md` ship-order blurb after 7P.0–7P.3 to CI → finish 7P.4–7P.8 → frontend → evals → HITL
- [x] 2.3 Update `slice-platform.md` Slice 8X exception note to match narrowed pre-7P.8 exception
- [x] 2.4 Skim `total.md` (and any other hard-coded “CI → evals → HITL → prod” chosen-path pointers) and align wording

## 3. Detail blueprint callouts (minimal)

- [x] 3.1 Add a one-line sequence note near the top of `slice8_eval.md` and `slice8_hitl.md`: follow chosen order in `slice8_X.md` (after 7P.8 on deploy-first)
- [x] 3.2 Confirm `slice8_ci.md` still reads as the first next implementation step; adjust only if it claims evals must precede VPS

## 4. Verification

- [x] 4.1 Re-read path TOC + `goal.md` + `production.md`: an operator after 7P.3 would start 8X.1.0, then finish prod, not evals
- [x] 4.2 Confirm job-search C-gate still lists evals as required (deferred sequencing, not removed)
- [x] 4.3 Confirm no application code, workflows, or `evals/` scaffolding was added in this change
