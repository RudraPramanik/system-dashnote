# Slice 9H.6 — Fixture Goldens (grade proof)
## Composer substages (themes → CI split → claim rule)

> **Parent index (order source):** [`slice9_H.md`](slice9_H.md) — phase **9H.6**, calendar position 6th.  
> **Operator default:** [`../blueprint9.md`](../blueprint9.md).  
> **Code anchors:** `evals/` fixture runner · `tests/ai/` · themes specified in `slice9_trust.md` 9H.1.4, `slice9_policy.md` 9H.2.3 and 9H.3.3, `slice9_cost.md` 9H.4.2  
> **Goal:** Pull-request CI can prove the harness claims without a live model key.  
> **This file is a prompt blueprint.** Implementing the tests is a later apply of these substages.

Order reminder: 9H.1 → 9H.2 → 9H.3 → 9H.4 → 9H.5 → 9H.6. This phase collects proof. It does not replace earlier phases.

**Claim rule:** Do not claim security B+, cost B+, or orchestration A- until the themes in 9H.6.1 pass in fixture CI.

---

## Sub-step 9H.6.1 — Required fixture themes

**Goal:** Four themes exist as automated fixtures.

| Theme | Expectation |
|-------|-------------|
| Model-invented workspace id | Service sees session workspace only, or the tool is denied |
| Role forbidden by note permissions | Code `forbidden`, no note commit |
| Poisoned retrieved content (switch workspace or skip approval) | No cross-tenant call; no commit without HITL |
| Budget exceeded | HTTP 429 or SSE `budget_exceeded`; model client not called |

**Fallback:** Unit tests count as fixtures when the golden JSONL runner cannot express the case. Each theme needs exactly one executable check, not both, if they would duplicate.

**Error boundary:** A theme must fail the run when the bad outcome happens. No `pytest.skip` on the happy path of CI.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.6.1 — Land the four harness fixture themes.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: the behavior each theme asserts already exists (9H.1, 9H.2, 9H.3, 9H.4).
If a behavior is missing, stop and name the earlier substep. Do not stub a passing test.

GOAL:
  Ensure automated fixture coverage for:
  1. Invented workspace id is not used.
  2. Forbidden role does not commit.
  3. Poisoned retrieved text cannot retarget tenant or skip HITL.
  4. Over-budget returns 429 or SSE budget_exceeded and does not call the model.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a new product phase beyond these fixtures.
  Do NOT require a live LLM API key.

VALIDATION GATE:
  The four checks run in the fixture/PR test command and fail when the protection is removed.
  Point each check at its file in the substep summary.

FALLBACK:
  Prefer the existing evals fixture runner. If it cannot encode a theme, a pytest
  in tests/ai/ is the fixture. Do not leave the theme as a comment only.

ERROR BOUNDARY:
  Do not skip a theme when secrets are absent. These tests must not need secrets.
```

---

## Sub-step 9H.6.2 — PR CI versus nightly

**Goal:** The four themes are on the pull-request path. Live red-team and judges stay operator/nightly.

**Fallback:** If CI time is tight, the four tests stay in the existing pytest CI job rather than a new workflow. Do not add a live-provider job to PR.

**Error boundary:** A nightly job failing must not be required for merge. A PR fixture failing must block merge.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.6.2 — Keep harness proof on fixture CI, live attacks off PR.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.6.1 checks exist.

GOAL:
  Wire the four themes into the pull-request test path that already runs fixture tests.
  Document that live jailbreak runs and LLM-as-judge suites are operator or nightly only.
  Do not add provider API keys to PR CI for this phase.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT make nightly judges a merge requirement.
  Do NOT require a live LLM key for the PR job.

VALIDATION GATE:
  The PR test docs or workflow include the four themes (or the pytest file that holds them).
  A nightly/live script, if mentioned, is labeled non-blocking.

FALLBACK:
  One extra pytest file in the current CI pytest invocation is enough.
  A new GitHub workflow is optional, not required.

ERROR BOUNDARY:
  Missing API keys in CI must not fail these fixtures. If a test tries to call
  a provider, that test is in the wrong lane — move it to nightly.
```

---

## Sub-step 9H.6.3 — Grade-claim gate

**Goal:** README, blueprint, or talk-track text that says B+ or A- is only allowed with the fixture result beside it.

**Fallback:** If no public README claim exists yet, add the rule to `blueprint9.md` status section only (one paragraph). Do not invent metrics.

**Error boundary:** A claim without a pointer to the passing themes is a doc bug. Remove the claim rather than shipping an unverified grade.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.6.3 — Forbid grade claims without the fixture themes.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.6.1 and 9H.6.2.

GOAL:
  Update the operator-facing status note (blueprint9 or the README AI section, only where
  a grade is actually stated) so security B+, cost B+, and orchestration A- are claimed
  only together with the four fixture themes passing.
  If the themes are not passing yet, the status stays "in progress" and does not use those grades.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT mark Blueprint 8 Tier 0 hire-ready from harness work alone.
  Do NOT require a live LLM key to justify a claim.

VALIDATION GATE:
  A reader can see either "grades not claimed yet" or "claimed because these checks pass"
  with file names. There is no bare "we are B+" sentence.

FALLBACK:
  Edit blueprint9.md status only. Leave the product README alone if it never stated these grades.

ERROR BOUNDARY:
  If fixtures are red, delete or downgrade the claim in the same change. Do not merge
  a claim that the tests contradict.
```
