## Context

See proposal.md for why. Runtime contracts already live in `ai-harness-trust`, `ai-harness-policy`, `ai-harness-injection`, and `ai-harness-budget`. Thin CI already runs `python -m pytest -q` and `python evals/run_eval.py --mode fixture` without live LLM keys (`.github/workflows/ci.yml`).

Existing coverage that already asserts the four behaviors (candidate canonicals):

| Theme | Strong existing check |
|-------|------------------------|
| Invented workspace | `tests/ai/test_harness_trust.py` — `test_search_uses_harness_workspace_not_foreign` (and schema omit) |
| Role forbidden | `tests/ai/test_harness_policy.py` — `test_forbidden_update_does_not_commit` |
| Poisoned retrieval | `tests/ai/test_injection_hygiene.py` — `test_poisoned_content_cannot_retarget_workspace` and/or `test_poisoned_content_cannot_skip_hitl` |
| Budget exceeded | `tests/ai/test_harness_budget_refusal.py` — `test_chat_over_budget_is_429_and_skips_the_model` (stream twin also exists) |

`evals/golden/` today covers RAG retrieval and tenant isolation via `/ai/test-search`, not tool-ACL / HITL / AI-budget route refusals. Encoding the four harness themes as JSONL goldens would force awkward HTTP fixtures or expand the eval runner beyond its current surface.

## Goals / Non-Goals

**Goals:**

- Designate exactly one executable check per theme as the 9H.6.1 grade-proof gate.
- Make the four checks discoverable and runnable together without a live LLM key.
- Fail closed when a protection is removed (no skip-for-missing-secrets).

**Non-Goals:**

- New harness runtime behavior (9H.1–9H.5 already shipped).
- 9H.6.2 workflow / nightly lane authorship (beyond documenting that these four already sit on the existing pytest PR path).
- 9H.6.3 B+/A- claim wording in blueprint9 / README.
- Expanding `evals/run_eval.py` to simulate LangGraph tools unless a theme truly cannot live as pytest (unlikely given the table above).
- Live jailbreak / LLM-as-judge suites.

## Decisions

### 1. Pytest is the fixture vehicle for all four themes

**Choice:** Use `tests/ai/` pytest as the designated fixture for every 9H.6.1 theme. Do not add parallel `evals/golden/` cases for the same themes.

**Why:** Blueprint fallback explicitly allows unit tests when the golden JSONL runner cannot express the case. These themes are harness/tool/route contracts already proven in-process with mocks. Duplicating them in JSONL would violate “exactly one executable check” and expand the eval CLI for little gain.

**Alternatives:** Force all four into `evals/run_eval.py --mode fixture` (rejected — wrong surface; runner is search/RAG oriented). Keep scattered tests with no catalog (rejected — discoverability requirement fails).

### 2. Thin catalog module over copy-paste rewrites

**Choice:** Add `tests/ai/test_harness_fixture_themes.py` as the grade-proof catalog. It either:

- imports and re-exports / wraps the four designated test callables from the existing modules, **or**
- defines four thin tests that call the same assertion helpers / patched paths with clear theme names,

and documents the theme → source mapping in the module docstring.

Prefer **nodeid-stable wrappers** that call into shared helpers or the existing test functions so removing the protection still fails. Do not leave “comment only” themes. Do not delete the original suites; they remain broader regressions outside the four designated gate checks.

**Why:** One `pytest tests/ai/test_harness_fixture_themes.py -q` command satisfies discoverability. Original files keep the richer edge cases (schema omit, stream twin, marker collision, etc.).

**Alternatives:** Pytest marker `harness_grade_theme` on existing tests only (acceptable fallback if wrappers create import cycles, but a dedicated file is clearer for operators). A markdown-only map with no aggregating file (fails “one documented command runs those four”).

### 3. Canonical one-check picks (locked unless a named check is missing)

| Theme | Designated check name (catalog) | Source of truth behavior |
|-------|----------------------------------|--------------------------|
| Invented workspace | `test_theme_invented_workspace_not_used` | Same assertion as `test_search_uses_harness_workspace_not_foreign` |
| Role forbidden | `test_theme_forbidden_role_does_not_commit` | Same assertion as `test_forbidden_update_does_not_commit` |
| Poisoned retrieval | `test_theme_poisoned_retrieval_cannot_retarget_or_skip_hitl` | Prefer one check that covers retarget **or** explicitly chains retarget + skip-HITL in one test so the gate stays a single nodeid; prefer retarget as primary if only one assertion body is reused, and assert no-commit-without-HITL in the same test body |
| Budget exceeded | `test_theme_budget_exceeded_skips_model` | Same assertion as `test_chat_over_budget_is_429_and_skips_the_model` (unary 429 is enough; stream twin stays outside the gate) |

If apply finds a designated source test missing or weak, stop and name the earlier 9H substep — do not stub a green theme.

### 4. CI wiring stays on the existing pytest job

**Choice:** Do not add a new GitHub workflow in 9H.6.1. Full `pytest -q` already runs these modules. Document the catalog path as the focused command. Defer explicit PR-versus-nightly labeling to 9H.6.2.

**Why:** Blueprint 9H.6.1 validation gate is “four checks run in the fixture/PR test command,” not “new workflow.” Thin CI already blocks on pytest failure.

### 5. No grade claims in this change

**Choice:** Catalog docstring / tasks summary may say “themes required before B+/A- claims” but MUST NOT assert that the product is B+ or A-. That is 9H.6.3.

## Risks / Trade-offs

- [Wrappers drift from source tests] → Prefer importing the existing test function or a shared helper; if wrapping, keep a one-line pointer comment to the source test name.
- [Poisoned theme wants two behaviors in one check] → Single catalog test may call both assertion paths sequentially; still one nodeid for the gate.
- [Operators look only in `evals/`] → Catalog docstring + tasks summary state pytest is the intentional fixture vehicle for harness themes; RAG goldens stay separate.
- [False green if catalog only documents] → Tasks require executing the four nodeids and confirming failure-mode intent (no skip).

## Migration Plan

1. Add the catalog module with four designated checks backed by existing harness assertions.
2. Run `python -m pytest tests/ai/test_harness_fixture_themes.py -q` (and the source files if helpers were extracted).
3. No deploy flag, Alembic, or compose change. Rollback = delete the catalog file; broader suites remain.

## Open Questions

None — fixture vehicle (pytest) and canonical source tests are locked above; 9H.6.2/9H.6.3 stay deferred.
