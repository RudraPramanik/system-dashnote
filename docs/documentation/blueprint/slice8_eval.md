# Slice 8X.2 — Evaluation Harness
## Final Cursor Prompts (5 Sub-steps, Measurable Quality, No Flaky PR CI)

> **Parent index:** [`slice8_X.md`](slice8_X.md)  
> **Aligns with:** `openspec/specs/ai-eval-harness` · [`goal.md`](goal.md) C-gate  
> **When to run:** After **8X.1** CI seatbelt recommended (can draft goldens earlier; wire to CI in 8X.2.4).  
> **Goal:** Golden corpus + runner — retrieval, tenant isolation, ≥5 agent trajectories (incl. forbid surprise create).

---

## Slice Overview

```
8X.2.0  Schema + folder laws     evals/golden/ contract; no live LLM required in PR
8X.2.1  Retrieval + tenant       ≥10 cases covering relevance + isolation themes
8X.2.2  Runner CLI               PASS: X/Y against configurable base URL + token
8X.2.3  Agent trajectories       ≥5 cases incl. forbid surprise create_note
8X.2.4  CI wire + docs           deterministic subset optional; honest pass-rate docs
```

**One Composer session ≈ one substep.**

---

## Readiness gate (before 8X.2.0)

| Prerequisite | Expected | Action if missing |
|--------------|----------|-------------------|
| Local API usable for live runs | `docker compose up`; `/health` 200 | Fix stack |
| Auth + notes + search/RAG | Existing slices | Do not rebuild RAG |
| Agent tools exist | Slice 6 `/ai/agent*` | Needed for 8X.2.3 |
| 8X.1 CI | Recommended | Wire deterministic evals in 8X.2.4 only after CI exists |
| `evals/` tree | May not exist yet | Create in 8X.2.0 |

**Verdict:** Start **8X.2.0**. Prefer offline/deterministic assertions where possible; live LLM runs are operator/nightly.

---

## ARCHITECTURE LAW — Slice 8X.2 Evals
### Paste as your FIRST message in every Composer session for 8X.2.x

```
ARCHITECTURE LAW — DashNoteSystem Slice 8X.2 (Eval harness).

CHAT ≠ AGENT:
  Keep /ai/chat* and /ai/agent* separate. Evals may call either surface
  intentionally — never delete or merge routes to “simplify testing.”

TENANCY:
  workspace_id from JWT wid / trusted auth only.
  Tenant-isolation cases MUST prove forged workspace in body/query does not
  expand retrieval beyond JWT workspace.
  Member must not retrieve another user’s private note content.

CI vs LIVE:
  PR CI must not require paid live LLM keys to stay green.
  Live evals (--base-url + token) are operator/nightly.
  Deterministic/fixture cases may join CI in 8X.2.4.

SCOPE:
  Prefer NEW: evals/golden/*.jsonl, evals/run_eval.py, evals/README.md
  Do not implement HITL, CD, or frontend here.
  Do not weaken production RBAC to make an eval pass.

FALLBACK:
  If API contract unclear → read OpenAPI /ai docs and ai.md first.
  If live LLM flakes → mark case as live-only; do not fail PR CI on it.
  If agent trajectory hard to assert without LLM → use recorded/fixture
  tool-call expectations where practical; document honesty in README.
```

---

## Fallbacks / out of scope

| Out of scope for 8X.2 | Defer to |
|-----------------------|----------|
| HITL interrupt/resume | `slice8_hitl.md` |
| Hybrid / rerank productization | 7R / Phase 2 |
| Claiming 100% pass when runner shows less | Forbidden — honest rate |
| Replacing chat with agent | Never |
| Multi-agent supervisor evals | Slice 9 |

---

## Sub-step 8X.2.0 — Schema + folder laws

**Goal:** Define machine-readable golden format and create `evals/` skeleton. No full corpus yet.

**Preferred layout:**

```
evals/
  README.md
  golden/
    retrieval.jsonl          # created/filled in 8X.2.1
    tenant_isolation.jsonl   # 8X.2.1
    agent_tools.jsonl        # 8X.2.3
  run_eval.py                # stub OK in 8X.2.0; real in 8X.2.2
```

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.0 — Define eval golden schema and create evals/ skeleton.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.

TASKS:
  1. CREATE evals/ directory structure (golden/, README.md).
  2. Document JSONL schema in README (required fields per case type:
     id, theme, auth role hints, request surface, expectations).
  3. CREATE empty or header-commented golden files listed above.
  4. Optionally stub evals/run_eval.py that prints “not implemented” and exits non-zero
     — full runner is 8X.2.2.
  5. State explicitly: PR CI will not require live LLM.

GATE:
  - Schema documented; folders exist.
  - No production RBAC changes.
```

**Gate:** Skeleton + schema docs exist.

**Commit hint:** `docs(evals): add golden schema and evals skeleton`

---

## Sub-step 8X.2.1 — Retrieval + tenant isolation goldens

**Goal:** ≥10 cases total covering retrieval relevance and tenant isolation (at least one automated isolation case).

**Surfaces to prefer:** `GET/POST /ai/test-search` and/or RAG chat — read OpenAPI / `ai.md` before inventing fields.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.1 — Author retrieval + tenant-isolation golden cases.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.2.0 schema exists.

TASKS:
  1. Fill evals/golden/retrieval.jsonl with relevance cases (expected note/chunk ids or content markers).
  2. Fill evals/golden/tenant_isolation.jsonl with ≥1 case:
     private note owned by A; member B must not see A’s private content.
  3. Include or document a case where forged workspace id in body/query must not leak cross-tenant data.
  4. Ensure ≥10 cases across retrieval + tenant themes combined (or clearly counted toward C-gate minimum with 8X.2.3).
  5. Do not modify notes/permissions.py to cheat isolation.

GATE:
  - Goldens committed and readable.
  - Tenant isolation theme present and automatable by the future runner.
```

**Gate:** Corpus themes present on disk.

**Commit hint:** `test(evals): add retrieval and tenant isolation goldens`

---

## Sub-step 8X.2.2 — Runner CLI

**Goal:** `evals/run_eval.py` executes retrieval/tenant goldens against `--base-url` + token; prints `PASS: X/Y` and failing ids.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.2 — Implement evals/run_eval.py for retrieval + tenant cases.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.2.1 goldens exist.

TASKS:
  1. Implement CLI: --base-url, --token (and any flags needed for fixture mode later).
  2. Load retrieval + tenant JSONL; execute against API; score pass/fail.
  3. Print aggregate PASS: X/Y and list failing case ids.
  4. Exit 0 only if all selected cases pass (or document --allow-fail for local iteration).
  5. Update evals/README.md with example PowerShell/bash commands.
  6. Agent trajectories may still be skipped until 8X.2.3 — print clear skip notice if so.

GATE:
  - Operator can run runner against local API and see summary.
  - Tenant isolation case is executed (not merely documented).
```

**Gate:** Runner works for retrieval/tenant sets.

**Commit hint:** `feat(evals): add run_eval CLI with pass/fail summary`

---

## Sub-step 8X.2.3 — Agent trajectories

**Goal:** ≥5 agent golden cases; extend runner to score them.

| # | Intent | Assert |
|---|--------|--------|
| 1 | Search / ask only | Search (or equiv.); **no** create/update |
| 2 | Explicit create | `create_note` when asked to create |
| 3 | **Forbid surprise create** | No `create_note` on plain question |
| 4 | Explicit update | `update_note` when asked to update |
| 5 | Stop / limit | Clean end / respects max iterations; no tool spam |

Prefer `evals/golden/agent_tools.jsonl`. Prefer deterministic/fixture trajectories for CI; live LLM optional.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.3 — Agent trajectory goldens + runner support.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.2.2 runner exists; Slice 6 agent works locally.

TASKS:
  1. Author ≥5 cases in evals/golden/agent_tools.jsonl including forbid-surprise-create.
  2. Extend run_eval.py to load and score agent cases (tool sequence / forbidden tools).
  3. Prefer fixture or recorded expectations for PR-safe runs; document live mode separately.
  4. Do not change chat routes; do not bypass NoteService in tools.

GATE:
  - Five trajectory themes present including forbid surprise create.
  - Runner reports agent case results in summary.
```

**Gate:** Agent goldens + runner coverage.

**Commit hint:** `test(evals): add agent trajectory goldens and scoring`

---

## Sub-step 8X.2.4 — CI wire + honest pass-rate docs

**Goal:** Optional deterministic subset in CI; document pass rate honestly for portfolio.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.4 — Wire deterministic evals to CI (optional) + document pass rate.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.1 CI exists; 8X.2.2–8X.2.3 runner works.

TASKS:
  1. If adding to CI: only deterministic/fixture cases — never require live LLM secrets.
  2. Update evals/README.md (and/or root README metrics placeholder) with how to record PASS: X/Y honestly.
  3. Do not claim 100% if runner shows less.
  4. Leave live `python evals/run_eval.py --base-url …` as operator docs.

GATE:
  - Pass-rate documentation path exists.
  - If CI wired: PR stays green without live LLM keys.
  - If CI not wired yet: README states how to run locally and that CI wire is pending — still OK for 8X.2 gate if corpus+runner complete.
```

**Gate:** Docs honest; CI either wired safely or explicitly deferred.

**Commit hint:** `ci(evals): optional deterministic eval job` or `docs(evals): document pass-rate recording`

---

## Slice 8X.2 Complete — Checklist

```
[ ] 8X.2.0 Schema + evals/ skeleton
[ ] 8X.2.1 Retrieval + tenant goldens
[ ] 8X.2.2 Runner PASS: X/Y
[ ] 8X.2.3 ≥5 agent trajectories incl. forbid surprise create
[ ] 8X.2.4 Honest docs (+ optional CI wire)
```

**Next:** [`slice8_hitl.md`](slice8_hitl.md) (8X.3) · Parent: [`slice8_X.md`](slice8_X.md)
