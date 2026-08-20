## 1. Slim TOC (`slice8_X.md`)

- [x] 1.1 Update `slice8_X.md` overview to link `slice8_ci.md` / `slice8_eval.md` / `slice8_hitl.md` for 8X.1–8X.3
- [x] 1.2 Replace embedded full 8X.1–8X.3 OBJECTIVE blocks with short summaries + “full prompts in …” pointers (keep global law, exception, 8X.4/8X.5)
- [x] 1.3 Confirm pre-7P.8 allowed/blocked and path order remain in the TOC

## 2. CI detail blueprint (`slice8_ci.md`)

- [x] 2.1 Write header, when-to-run, readiness gate, link to `slice8_X.md` + `slice-platform.md` §7P.7
- [x] 2.2 Write paste-first ARCHITECTURE LAW (no prod secrets, no SSH, don’t break compose, no live LLM for green CI)
- [x] 2.3 Author substages 8X.1.0–8X.1.3 with OBJECTIVE prompts, file/task hints, gates, fallbacks
- [x] 2.4 Add out-of-scope / complete checklist sections

## 3. Eval detail blueprint (`slice8_eval.md`)

- [x] 3.1 Write header, readiness gate, link to `slice8_X.md` + `ai-eval-harness` intent
- [x] 3.2 Write paste-first ARCHITECTURE LAW (tenant from JWT, chat≠agent, no live LLM required in PR CI)
- [x] 3.3 Author substages 8X.2.0–8X.2.4 with OBJECTIVE prompts, corpus minima, runner gate, agent trajectory table, fallbacks
- [x] 3.4 Add out-of-scope / complete checklist sections

## 4. HITL detail blueprint (`slice8_hitl.md`)

- [x] 4.1 Write header, readiness gate (8X.1–8X.2 recommended), link to `slice8_X.md` + agent paths
- [x] 4.2 Write paste-first ARCHITECTURE LAW (chat untouched, tools→services, tenant freeze, FE out of gate)
- [x] 4.3 Author substages 8X.3.1–8X.3.4 with OBJECTIVE prompts, proposed `approval_required`, resume-by-thread, script/test gate, fallbacks
- [x] 4.4 Add out-of-scope / complete checklist sections

## 5. Discoverability + verify

- [x] 5.1 Ensure `total.md` / `goal.md` / `production.md` mention or still reach Slice 8X (add detail-file names only if missing)
- [x] 5.2 Skim all four blueprint files against this change’s specs (ci/eval/hitl/path-toc)
- [x] 5.3 Confirm docs-only: no `.github/workflows`, no `evals/` runtime code, no agent HITL code in this change
