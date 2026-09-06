## Context

See `proposal.md` for motivation. Platform scripts/workflows for 7P are largely present (`smoke_prod.py`, CI/CD, prod compose), but A-gate live evidence and `goal.md` checkboxes are still open. `evals/` is missing despite `ai-eval-harness` main specs. Sibling `dashnotes` is the FE; this OpenSpec root’s apply edits are limited to `dashnotesystemv1`. Locked calendar: deploy-first — prove A → B → C → D; Tier 1 HITL is out of scope.

## Goals / Non-Goals

**Goals:**

- Close Tier 0 with operator-provable A/B/C/D evidence and honest trackers.
- Ship a usable `evals/` harness (fixture + live) meeting C-gate without weakening RBAC.
- Keep Alive: local Compose, chat≠agent, CI without live LLM keys.

**Non-Goals:**

- HITL interrupt/resume (Tier 1 / 8X.3).
- Wiring fixture evals as a required PR-fail job (document readiness; Tier 1 may wire).
- GraphRAG, multi-agent, Lite Upwork template.
- Large FE redesign inside this repo (sibling owns UI code).

## Decisions

### 1. Sequence: A → B → C → D (deploy-first)

- **Choice:** Prove HTTPS smoke before treating evals/HITL as portfolio-blocking; usually prove FE demo before C-gate live runs against prod.
- **Why:** Matches blueprint8 / slice8_X chosen path; keeps stranger demo Alive while measuring.
- **Alternative:** AI-depth-first (evals before live URL) — rejected unless operator explicitly switches.

### 2. Evals live outside `src/` with thin CLI

- **Choice:** `evals/golden/*.jsonl`, `evals/run_eval.py`, `evals/README.md`; import via documented `PYTHONPATH=src` / module run.
- **Why:** Aligns with slice8_eval; avoids polluting `src/ai` with operator harness.
- **Alternative:** pytest-only package under `tests/` — weaker as a portfolio CLI story (`PASS: X/Y`).

### 3. Fixture + live modes in one runner; C-gate prefers live proof

- **Choice:** Dual modes now; C-gate documentation uses live `--base-url` summary when available; fixture keeps PR/local deterministic.
- **Why:** Spec + Alive law; agent trajectory goldens (≥5) deferred to Tier 1 deepeners even if schema stubs are harmless later.
- **Alternative:** Live-only harness — flakes and blocks CI safety narrative.

### 4. Tenant isolation via dual tokens or fixtures

- **Choice:** Live isolation cases use two JWTs (owner vs member) in one workspace; fixture mode may record responses.
- **Why:** Required by existing harness specs; never forge `workspace_id` from body.
- **Alternative:** Docs-only isolation — rejected.

### 5. Sibling FE is proof-tracked here, coded there

- **Choice:** This change ensures `CORS_ORIGINS` and docs/trackers; B UI/deploy tasks are operator/sibling work referenced from tasks, not applied as edits under this root.
- **Why:** `allowedEditRoots` is `dashnotesystemv1`; FE already exists as `dashnotes`.
- **Alternative:** Monorepo FE rewrite here — out of product layout.

### 6. Tracker as gate source of truth

- **Choice:** Flip `goal.md` (and README claims) only after evidence; production.md may say 7P.8 done for files while A-gate live claim stays open until smoke.
- **Why:** Separates “machinery shipped” from “live proven.”

## Risks / Trade-offs

- **[Risk] VPS/hosted credentials unavailable during apply** → Mitigation: keep A tasks operator-runnable; code/docs for C/D can progress locally; do not fake live URLs.
- **[Risk] Live evals flake on LLM/embed lag** → Mitigation: retrieval cases prefer search/test-search where possible; document indexing wait; honest pass rate; mark LLM-heavy cases live-only.
- **[Risk] B-gate blocked on sibling FE gaps** → Mitigation: track explicitly; API CORS fix in this repo; do not claim Tier 0 until demo works.
- **[Risk] Scope creep into HITL/agent traj** → Mitigation: tasks stop at C1–C4 + packaging; traj ≥5 is Tier 1.

## Migration Plan

1. Operator: confirm hosted env + deploy tag/smoke on HTTPS; update A-gate.
2. Align CORS + FE demo; update B-gate.
3. Land `evals/` + goldens; run live summary; document rate; update C-gate.
4. README / talk track / topics; update D-gate.
5. Rollback: revert evals/docs commits; leave prod infra as-is (no schema migration expected).

## Open Questions

- Exact production API/app hostnames for README (fill when smoke/FE TLS proven).
- Whether first C-gate live run targets local Compose or prod URL (either acceptable if documented; prefer prod when Alive).
