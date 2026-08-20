# Slice 8X.2 — Evaluation Harness
## Final Cursor Prompts (5 Sub-steps, Measurable Quality, No Flaky PR CI)

> **Parent index:** [`slice8_X.md`](slice8_X.md)  
> **Sequence (chosen / deploy-first):** After **7P.8** (and usually frontend) per [`slice8_X.md`](slice8_X.md) — do not start immediately after 8X.1.  
> **Aligns with:** `openspec/specs/ai-eval-harness` · [`goal.md`](goal.md) C-gate  
> **When to run:** After production smoke on the chosen path (prefer live `--base-url`); 8X.1 CI recommended before wiring fixture evals in 8X.2.4.  
> **Goal:** Golden corpus + runner — retrieval, tenant isolation, ≥5 agent trajectories (incl. forbid surprise create).  
> **Modes:** `fixture` (PR-safe) vs `live` (operator/nightly). Schema + seed strategy land in **8X.2.0** before filling goldens.

---

## Slice Overview

```
8X.2.0  Schema + folder laws     modes, trajectory fields, seed/fixture IDs, PYTHONPATH docs
8X.2.1  Retrieval + tenant       ≥10 cases; dual-token or fixture for isolation
8X.2.2  Runner CLI               fixture|live; PASS: X/Y; src on path
8X.2.3  Agent trajectories       ≥5 cases scored via forbidden/required/sequence_mode
8X.2.4  CI wire + docs           PR = fixture only; live = operator/nightly; honest pass-rate
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
  Isolation cases that compare two actors MUST be runnable via dual tokens
  (live) OR fixture/recorded responses — never documentation-only.

RUNNER MODES:
  Distinguish fixture (deterministic / recorded) vs live (--base-url + token(s)).
  Exact CLI flag names may vary (--mode fixture|live or equivalent) but BOTH modes MUST exist.
  PR CI runs fixture/deterministic only — never require live LLM keys for green PR.

SEED / FIXTURE IDS:
  Golden note_id / chunk_id (and similar) MUST come from a documented seed step
  OR be avoided via fixture/recorded mode.
  Do NOT assume arbitrary IDs exist in a fresh environment.

TRAJECTORY SCHEMA (required fields for agent cases):
  forbidden_tools: string[]
  required_tools: string[]
  sequence_mode: "exact" | "subset"
  Optional extras allowed; these three MUST be present and scored by the runner.
  Vague “assert tool sequence” without these fields is forbidden.

IMPORT PATH:
  Document how to run the runner with src importable (PYTHONPATH=src or python -m …).
  evals/ may live outside src/ — README must prevent ModuleNotFoundError.

CI vs LIVE:
  PR CI must not require paid live LLM keys to stay green.
  Live evals are operator/nightly.
  Deterministic/fixture cases may join CI in 8X.2.4.

SCOPE:
  Prefer NEW: evals/golden/*.jsonl, evals/run_eval.py, evals/README.md
  Do not implement HITL, CD, or frontend here.
  Do not weaken production RBAC to make an eval pass.
  Do NOT treat docs/documentation/blueprint/new.md as source of truth.

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
| Live LLM as PR-blocking gate | Never |

---

## Sub-step 8X.2.0 — Schema + folder laws

**Goal:** Define machine-readable golden format (modes, trajectory fields, seed strategy) and create `evals/` skeleton. No full corpus yet.

**Preferred layout:**

```
evals/
  README.md                  # schema + modes + seed + PYTHONPATH how-to
  golden/
    retrieval.jsonl          # filled in 8X.2.1
    tenant_isolation.jsonl   # 8X.2.1
    agent_tools.jsonl        # 8X.2.3
  run_eval.py                # stub OK in 8X.2.0; real in 8X.2.2
  # optional: fixtures/ or seed script path documented in README
```

**Locked schema (document in README — extend, don’t drop):**

| Case type | Required / notable fields |
|-----------|---------------------------|
| Common | `id`, `theme`, `mode_hint` (`fixture` \| `live` \| `either`), request surface |
| Retrieval | expectations (ids **or** content markers); if ids → seed or fixture strategy |
| Tenant | dual-auth fields **or** `fixture_ref`; forged-workspace case |
| Agent | `forbidden_tools`, `required_tools`, `sequence_mode` (`exact` \| `subset`) |

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.0 — Define eval golden schema and create evals/ skeleton.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.

TASKS:
  1. CREATE evals/ directory structure (golden/, README.md).
  2. Document JSONL schema in README including:
     - runner modes: fixture vs live (CLI flags may be finalized in 8X.2.2)
     - trajectory fields: forbidden_tools, required_tools, sequence_mode
     - seed-or-fixture strategy for note_id / chunk_id
     - how to invoke with PYTHONPATH=src (or equivalent) so src imports work
  3. CREATE empty or header-commented golden files listed above.
  4. Optionally stub evals/run_eval.py that prints “not implemented” and exits non-zero
     — full runner is 8X.2.2.
  5. State explicitly: PR CI will not require live LLM; fixture mode is the PR path.

GATE:
  - Schema documented with modes, trajectory fields, and seed/fixture ID strategy.
  - Folders exist; import-path docs present.
  - No production RBAC changes.
```

**Gate:** Skeleton + schema docs exist (contracts before corpus).

**Commit hint:** `docs(evals): add golden schema and evals skeleton`

---

## Sub-step 8X.2.1 — Retrieval + tenant isolation goldens

**Goal:** ≥10 cases total covering retrieval relevance and tenant isolation (at least one **automatable** isolation case).

**Surfaces to prefer:** `GET/POST /ai/test-search` and/or RAG chat — read OpenAPI / `ai.md` before inventing fields.

**Tenant automation contract:** each isolation case MUST specify either:

- Live: how to obtain token A + token B (two users/workspaces), **or**
- Fixture: recorded responses / fixture refs that prove B cannot see A’s private content

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.1 — Author retrieval + tenant-isolation golden cases.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.2.0 schema exists (modes + seed strategy documented).

TASKS:
  1. Fill evals/golden/retrieval.jsonl with relevance cases.
     Prefer content markers or seeded IDs — never orphan hardcoded IDs without seed/fixture.
  2. Fill evals/golden/tenant_isolation.jsonl with ≥1 case:
     private note owned by A; member B must not see A’s private content.
     Include dual-token fields OR fixture_ref so the runner can execute it.
  3. Include or document a case where forged workspace id in body/query must not leak cross-tenant data.
  4. Ensure ≥10 cases across retrieval + tenant themes combined (or clearly counted toward C-gate minimum with 8X.2.3).
  5. Do not modify notes/permissions.py to cheat isolation.

GATE:
  - Goldens committed and readable against 8X.2.0 schema.
  - Tenant isolation theme present and automatable (dual-token or fixture) — not README-only.
```

**Gate:** Corpus themes present on disk and runnable by design.

**Commit hint:** `test(evals): add retrieval and tenant isolation goldens`

---

## Sub-step 8X.2.2 — Runner CLI

**Goal:** `evals/run_eval.py` supports fixture and live modes; executes retrieval/tenant goldens; prints `PASS: X/Y` and failing ids.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.2 — Implement evals/run_eval.py for retrieval + tenant cases.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.2.1 goldens exist.

TASKS:
  1. Implement CLI with explicit fixture vs live support
     (e.g. --mode fixture|live, plus --base-url / --token / dual-token flags as needed).
  2. Load retrieval + tenant JSONL; score pass/fail per schema expectations.
  3. For live tenant cases: accept two tokens when cases require them.
  4. For fixture cases: do not call live LLM; use recorded/fixture data.
  5. Print aggregate PASS: X/Y and list failing case ids.
  6. Exit 0 only if all selected cases pass (or document --allow-fail for local iteration).
  7. Update evals/README.md with PowerShell/bash examples including PYTHONPATH=src
     (or documented equivalent).
  8. Agent trajectories may still be skipped until 8X.2.3 — print clear skip notice if so.

GATE:
  - Operator can run fixture mode without live LLM.
  - Operator can run live mode against local API when desired.
  - Tenant isolation case is executed (not merely documented).
```

**Gate:** Runner works for retrieval/tenant sets in both modes (as applicable).

**Commit hint:** `feat(evals): add run_eval CLI with pass/fail summary`

---

## Sub-step 8X.2.3 — Agent trajectories

**Goal:** ≥5 agent golden cases; extend runner to score them via locked schema fields.

| # | Intent | Assert via schema |
|---|--------|-------------------|
| 1 | Search / ask only | `required_tools` includes search (or equiv.); `forbidden_tools` includes create/update |
| 2 | Explicit create | `required_tools` includes `create_note` |
| 3 | **Forbid surprise create** | `forbidden_tools` includes `create_note` on plain question |
| 4 | Explicit update | `required_tools` includes `update_note` |
| 5 | Stop / limit | Clean end / no tool spam — express with required/forbidden + sequence_mode as practical |

Prefer `evals/golden/agent_tools.jsonl`. Prefer fixture trajectories for CI; live LLM optional.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.3 — Agent trajectory goldens + runner support.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.2.2 runner exists; Slice 6 agent works locally.

TASKS:
  1. Author ≥5 cases in evals/golden/agent_tools.jsonl including forbid-surprise-create.
     Each case MUST set forbidden_tools, required_tools, sequence_mode.
  2. Extend run_eval.py to load and score agent cases using those fields
     (exact vs subset sequence per sequence_mode) — not prose-only checks.
  3. Prefer fixture or recorded expectations for PR-safe runs; document live mode separately.
  4. Do not change chat routes; do not bypass NoteService in tools.

GATE:
  - Five trajectory themes present including forbid surprise create.
  - Runner reports agent case results using the locked schema fields.
```

**Gate:** Agent goldens + schema-based runner coverage.

**Commit hint:** `test(evals): add agent trajectory goldens and scoring`

---

## Sub-step 8X.2.4 — CI wire + honest pass-rate docs

**Goal:** Optional fixture/deterministic subset in CI; live remains operator/nightly; honest pass-rate docs.

---

```
ROLE: Senior applied AI engineer.

OBJECTIVE: Slice 8X.2.4 — Wire fixture evals to CI (optional) + document pass rate.

Paste ARCHITECTURE LAW — Slice 8X.2 Evals first.
Prerequisite: 8X.1 CI exists; 8X.2.2–8X.2.3 runner works.

TASKS:
  1. If adding to CI: ONLY fixture/deterministic cases — never require live LLM secrets
     or a full live auth stack for green PR.
  2. Document live operator/nightly command separately (e.g. --mode live --base-url …).
  3. Update evals/README.md (and/or root README metrics placeholder) with how to record
     PASS: X/Y honestly.
  4. Do not claim 100% if runner shows less.

GATE:
  - Pass-rate documentation path exists.
  - If CI wired: PR stays green without live LLM keys (fixture only).
  - If CI not wired yet: README states how to run locally and that CI wire is pending —
    still OK for 8X.2 gate if corpus+runner complete.
```

**Gate:** Docs honest; CI either wired safely (fixture-only) or explicitly deferred.

**Commit hint:** `ci(evals): optional deterministic eval job` or `docs(evals): document pass-rate recording`

---

## Slice 8X.2 Complete — Checklist

```
[ ] 8X.2.0 Schema + modes + seed/fixture + PYTHONPATH docs; evals/ skeleton
[ ] 8X.2.1 Retrieval + tenant goldens (isolation automatable)
[ ] 8X.2.2 Runner PASS: X/Y with fixture|live
[ ] 8X.2.3 ≥5 agent trajectories scored via forbidden/required/sequence_mode
[ ] 8X.2.4 Honest docs (+ optional fixture-only CI wire)
```

**Next:** [`slice8_hitl.md`](slice8_hitl.md) (8X.3) · Parent: [`slice8_X.md`](slice8_X.md)
