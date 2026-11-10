## Why

9H.1–9H.5.3 already bind tenant, enforce tool ACL and injection hygiene, refuse over-budget completions, degrade safely, and thin routes behind one control plane. Blueprint 9 still forbids claiming security B+, cost B+, or orchestration A- until **9H.6** fixture themes prove those protections in pull-request CI without a live model key. The next locked substep is **9H.6.1** (`docs/documentation/blueprint/slice9_eval.md`, indexed by `slice9_H.md`): land exactly four automated fixture themes as the grade-proof suite.

## What Changes

- **9H.6.1** — Required fixture themes:
  - Ensure one executable, no-secrets check exists for each theme:
    1. Model-invented workspace id → session workspace only, or tool denied
    2. Role forbidden by note permissions → code `forbidden`, no note commit
    3. Poisoned retrieved content (switch workspace or skip approval) → no cross-tenant call; no commit without HITL
    4. Budget exceeded → HTTP 429 or SSE `budget_exceeded`; model client not called
  - Prefer the existing `evals/` fixture runner when a theme fits JSONL goldens; otherwise a pytest under `tests/ai/` is the fixture (unit tests count). Do not duplicate the same theme as both golden and pytest.
  - Each theme must fail the run when the protection is removed. No `pytest.skip` on the happy path of CI. No live LLM API key.
  - Point each theme at its canonical file/test in the change summary so operators can find the proof.
- Behaviors the themes assert already shipped in 9H.1–9H.4. This substep packages and gates proof; it does not reimplement harness runtime.
- Keep `/ai/chat*` and `/ai/agent*` both mounted. No second agent framework. No grade claims yet (9H.6.3). No PR-versus-nightly workflow split yet (9H.6.2) beyond ensuring these four are runnable without secrets.
- **Out of scope:** 9H.6.2 CI/nightly lane docs and workflow changes beyond naming the four themes’ command; 9H.6.3 grade-claim status wording; live jailbreak / LLM-as-judge suites; collapsing chat into agent; Alembic; compose changes; Qdrant writes; Slice 8; Slice 9; billing; new permission engines.

## Capabilities

### New Capabilities

- `ai-harness-fixture-themes`: Four no-secrets automated fixture themes that prove invented-workspace, role-forbidden, poisoned-retrieval, and over-budget protections for Blueprint 9 grade claims.

### Modified Capabilities

- _(none)_ — earlier harness capabilities already define the runtime behaviors; this change adds the cross-cutting proof suite, not new deny/allow contracts.

## Impact

- Code / tests: designate or add one canonical executable check per theme under `evals/` and/or `tests/ai/` (exact layout in design). Prefer reusing existing harness tests from 9H.1–9H.4 rather than inventing parallel stubs. No ARQ worker rewrite. No Qdrant (`notes_chunks` / `files_chunks`) change.
- APIs: `/ai/chat*` and `/ai/agent*` both remain. Client contracts for tenant bind, `forbidden`, HITL, and `budget_exceeded` stay unchanged.
- CI: the four checks must run without a live LLM key and must fail when protections are removed. Wiring into a new GitHub workflow is optional and deferred to 9H.6.2 if the existing pytest path already covers them.
- Docs: theme → file mapping in the change summary; no bare B+/A- claims (9H.6.3).
- Dependencies: no Alembic, no compose service, no provider keys in PR.
- Blueprint map: **9H.6.1 only**.
