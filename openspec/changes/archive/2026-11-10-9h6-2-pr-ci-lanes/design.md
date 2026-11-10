## Context

See proposal.md for why. 9H.6.1 already ships `tests/ai/test_harness_fixture_themes.py` with four designated theme checks. Thin CI (`.github/workflows/ci.yml`) already:

- runs on `pull_request` and push to `stage` / `main` / `production`
- executes `python -m pytest -q` (with a small JSONB allowlist ignore set) then `python evals/run_eval.py --mode fixture`
- requires no live LLM / VPS / SSH secrets

Operator docs already distinguish L0 fixture (PR) from L1 live / L2 judges / Langfuse faithfulness / RAGAS (operator or nightly) in `evals/README.md` and `evals/BLUEPRINT.md`. What is missing is an explicit Blueprint 9 harness-lane statement that ties the four themes to the merge gate and keeps live red-team / judges non-blocking.

## Goals / Non-Goals

**Goals:**

- Make the PR-versus-nightly split for harness proof unmistakable in CI comments and operator-facing docs.
- Keep the four themes on the existing merge-blocking pytest path without new secrets.
- Label any mentioned live jailbreak / LLM-as-judge / live-eval path as non-blocking.

**Non-Goals:**

- New harness runtime behavior.
- A new merge-required GitHub workflow or scheduled nightly Actions job (optional later; not required for 9H.6.2).
- Implementing live jailbreak suites.
- 9H.6.3 B+/A- claim wording.
- Changing the thin-CI ignore allowlist or Dockerfile parity rules.

## Decisions

### 1. Stay on the existing pytest job — no new PR workflow

**Choice:** Treat `.github/workflows/ci.yml`’s existing `python -m pytest -q` step as the merge-blocking vehicle for the four themes. Do not add a separate harness-only GitHub workflow for PRs.

**Why:** Blueprint 9H.6.2 fallback says one extra pytest file in the current CI invocation is enough; a new workflow is optional. Themes already live under `tests/ai/` and are collected by that job.

**Alternatives:** Dedicated `harness-themes` job that re-runs only the catalog file (rejected — duplicate wall-clock and no stronger merge signal). Move themes into `evals/run_eval.py --mode fixture` (rejected — 9H.6.1 locked pytest as the vehicle).

### 2. Documentation + workflow header annotation over new nightly Actions

**Choice:** Update:

1. Header / comments on `.github/workflows/ci.yml` to name the harness grade-proof catalog (`tests/ai/test_harness_fixture_themes.py`) as part of the blocking pytest lane, and to state that live jailbreak / LLM-as-judge are out of this workflow and non-blocking.
2. A short operator-facing note in `evals/README.md` (preferred, already owns lane language) that explicitly lists Blueprint 9 harness themes on the PR pytest path and points live red-team / judges to existing non-merge lanes. Optionally a one-paragraph cross-link from `docs/documentation/blueprint/slice9_eval.md` or `blueprint9.md` Alive/CI table if that file still implies the split is unfinished — without claiming B+/A- grades.

Do **not** author a scheduled nightly GitHub Actions workflow in this change.

**Why:** Nightly live suites already have CLIs (`run_eval.py --mode live`, `run_quality.py`, `run_langfuse_faithfulness.py`, `run_ragas.py`). Blueprint validation is “PR docs/workflow include the four themes” and “nightly/live labeled non-blocking,” not “ship a cron job.”

**Alternatives:** Create `.github/workflows/nightly-evals.yml` as `workflow_dispatch` / schedule with secrets (deferred — useful later, out of 9H.6.2 minimum, and easy to accidentally mark required). Edit only OpenSpec main specs with no human-facing CI comment (rejected — operators read `ci.yml` and `evals/README.md`).

### 3. Focused catalog command stays the operator shortcut

**Choice:** Keep documenting `python -m pytest tests/ai/test_harness_fixture_themes.py -q` as the focused four-theme command. Full PR proof remains the thin CI pytest invocation.

**Why:** Already locked by 9H.6.1 discoverability. 9H.6.2 only places that catalog on the merge lane narrative.

### 4. No grade claims in this change

**Choice:** Docs may say the themes are required before B+/A- claims, but MUST NOT assert the product is B+ or A-. That is 9H.6.3.

## Risks / Trade-offs

- [Operators think themes are not on CI because there is no dedicated job] → Mitigate with explicit `ci.yml` comment naming the catalog file and the blocking pytest step.
- [Someone adds a nightly Actions job later and marks it required] → Spec forbids merge-required live/judge checks; tasks document the non-blocking label rule.
- [Docs drift between `evals/README.md` and blueprint9] → Prefer one primary operator paragraph in `evals/README.md` plus a thin blueprint cross-link if needed; do not duplicate long tables.
- [False sense that jailbreak coverage exists in CI] → Explicitly state live jailbreak is not implemented as a PR gate and remains operator/nightly when/if run.

## Migration Plan

1. Annotate `ci.yml` and update operator lane docs as decided above.
2. Confirm locally: `python -m pytest tests/ai/test_harness_fixture_themes.py -q` still passes without live keys; sanity-check that the file is not under a CI `--ignore` path.
3. No Alembic, compose, or deploy change. Rollback = revert doc/comment edits; themes and thin CI remain.

## Open Questions

None — stay on existing pytest; no new nightly Actions in this substep; grade claims deferred to 9H.6.3.
