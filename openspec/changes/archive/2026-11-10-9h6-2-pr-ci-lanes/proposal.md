## Why

9H.6.1 already landed four no-secrets harness fixture themes under `tests/ai/test_harness_fixture_themes.py`, and thin CI already runs `python -m pytest -q` on pull requests. Blueprint 9’s next locked substep is **9H.6.2** (`docs/documentation/blueprint/slice9_eval.md`, indexed by `slice9_H.md`): make the PR-versus-nightly split explicit so harness proof blocks merge, while live jailbreak / LLM-as-judge work stays operator or nightly and never becomes a merge requirement or a reason to put provider keys on PR CI.

## What Changes

- **9H.6.2** — PR CI versus nightly lanes for harness proof:
  - Confirm (and document) that the four 9H.6.1 themes ride the existing pull-request test path (thin CI pytest job). A failing theme MUST block merge.
  - Document that live jailbreak runs, live-mode evals, and LLM-as-judge suites are operator or nightly only and MUST NOT be required for merge.
  - Do not add provider API keys, production VPS credentials, or SSH to PR CI for this phase.
  - Do not invent a merge-blocking nightly GitHub job. A new workflow is optional; labeling and docs are enough when themes already run under `pytest -q`.
  - If any nightly/live script is mentioned, label it non-blocking.
- Keep `/ai/chat*` and `/ai/agent*` both mounted. No second agent framework. No B+/A- grade claims (9H.6.3).
- **Out of scope:** 9H.6.3 grade-claim status wording; implementing live jailbreak suites; making RAGAS / DeepEval / Langfuse faithfulness a merge gate; collapsing chat into agent; Alembic; compose changes; Qdrant writes; Slice 8; Slice 9; billing; new permission engines; rewriting harness runtime from 9H.1–9H.5.

## Capabilities

### New Capabilities

- `ai-harness-ci-lanes`: Operator-visible PR-versus-nightly lane split for Blueprint 9 harness proof — fixture themes on the merge-blocking PR path; live red-team and LLM-as-judge off PR and non-blocking.

### Modified Capabilities

- `ai-harness-fixture-themes`: Add the requirement that the four designated themes MUST execute on the pull-request CI path that blocks merge, without live provider keys.
- `thin-ci`: Clarify that harness grade-proof themes are covered by the existing blocking pytest job, and that live/judge/nightly lanes MUST NOT be added as merge requirements or as PR secret dependencies.

## Impact

- CI / docs: annotate `.github/workflows/ci.yml` and/or operator docs (`evals/README.md`, Blueprint 9 / `slice9_eval` cross-links as needed) so PR vs nightly is unmistakable. Prefer comment + short doc updates over a new workflow when pytest already covers the themes.
- Code / runtime: no harness behavior change expected. No ARQ rewrite. No Qdrant (`notes_chunks` / `files_chunks`) change.
- APIs: `/ai/chat*` and `/ai/agent*` both remain. Client contracts unchanged.
- Secrets: PR CI stays free of live LLM keys, VPS credentials, and SSH. Nightly/live remains optional and labeled non-blocking.
- Tests: verify the four theme nodeids still run under the PR pytest invocation without secrets; do not add a merge-required live job.
- Blueprint map: **9H.6.2 only**.
