## Context

See `proposal.md` for why. Current tree: ~45 files under `docs/` plus root `n.md`. Specs still require historical Composer files (`slice8_*.md`, `ship-plan.md`) and a dual observability path (`observe.md` + `observability.md`). In-flight `production-ai-observability` writes `docs/documentation/observe.md`. Git already stores deleted history; this change does not add an in-repo `docs/archive/` folder.

## Goals / Non-Goals

**Goals:**

- Merge unique facts into keep-set files *before* any delete, so operators do not lose a still-true law.
- Rewrite every in-repo markdown / config pointer in the same pass (no stub redirect files).
- Leave `observe.md` as the observability path so the in-flight observability change does not retarget.
- Update `openspec/config.yaml` canonical-docs list to match the keep-set.

**Non-Goals:**

- Rewriting architecture prose in `system.md` / `ai.md` except for merged LLM-ops notes and link tables.
- Deleting or rewriting OpenSpec `changes/archive/` or main specs except via this change’s deltas at apply/archive time.
- Merging `qs.md` / `qs2.md` / `qs3.md` (unique Q&A format; not the stale slice tree).

## Decisions

### 1. Delete historical slices; do not keep an in-repo archive folder

**Choice:** Remove shipped Composer prompts (`slice1`–`slice7`, `slice8_*`, `total.md`, `observation-blueprint.md`, `slice-platform.md`, `new.md`) and `n.md`. Git history is the archive.

**Why:** An `docs/archive/` folder would keep the same discoverability problem (agents still open stale prompts).

**Alternative considered:** Move files to `docs/archive/`. Rejected — still clutters search and link graphs.

### 2. Keep `observe.md`; fold `observability.md` into it

**Choice:** Copy any unique operator commands/diagrams from `docs/observability.md` into `docs/documentation/observe.md`, then delete `observability.md`.

**Why:** Canonical docs and the in-flight observability change already treat `observe.md` as the agent/operator target.

**Alternative considered:** Keep `observability.md` as the human runbook. Rejected — two files is the duplication we are removing.

### 3. Goal.md absorbs ship-plan; no stub `ship-plan.md`

**Choice:** Diff `docs/ship-plan.md` against `goal.md` / `blueprint8.md`; lift still-open unique boxes into `goal.md`; delete `ship-plan.md`.

**Why:** Three overlapping trackers (blueprint8 / goal / ship-plan) is the main “repeated” complaint. Specs already need the lock moved off ship-plan.

**Alternative considered:** Slim ship-plan to a one-pager that only links blueprint8. Rejected — still a fourth entry in the README.

### 4. Merge NIM / hang notes into `ai.md`; drop incident timeline as a standalone file

**Choice:** Keep durable laws (`LLM_MODEL` + `LLM_MODEL_FALLBACKS`, HTTP 410 and wall-clock timeout, do not pin one NIM id). Do not copy the full 2026-08 incident table unless a one-line “catalog ids EOL” warning remains useful.

**Why:** `issue_solve.md` and `nvidia.md` overlap each other and `ai.md` settings tables.

### 5. Link rewrite is grep-driven; no markdown stubs

**Choice:** After merges, search the repo (excluding `openspec/changes/archive/`) for deleted basenames and rewrite. Prefer existing keep-set targets. Do not leave “this file moved” stubs.

**Why:** Stubs become a second docs tree.

### 6. Keep interview Q&A pack

**Choice:** Leave `qs.md`, `qs2.md`, `qs3.md`, `interview-talk-track.md`, and `interview-evidence-guide.md`. They are complementary (Q&A vs pitch vs demo playbook), not leftover implementation prompts.

**Why:** The request was to drop repeated *and not needed now* files; interview pack is still used.

### 7. UML index lives in `diagrams.md`

**Choice:** Move the diagram table from `docs/uml/README.md` into `diagrams.md` if missing; point at `docs/documentation/lld.md` (not `src/docs/lld.md`); delete `README.md`.

## Risks / Trade-offs

- **[Risk] Unique open checkbox lives only in ship-plan → Mitigation:** Explicit lift pass before delete; compare remaining ⬜ items in goal.md.
- **[Risk] Unique observe runbook command exists only in `observability.md` → Mitigation:** Side-by-side section pass before delete.
- **[Risk] In-flight `production-ai-observability` still mentions `observability.md` → Mitigation:** Keep `observe.md` path; after this change, that workstream should only edit `observe.md`.
- **[Risk] Archived OpenSpec changes still link deleted files → Mitigation:** Out of scope; archives are historical. Live `openspec/config.yaml` and keep-set docs must not 404.
- **[Trade-off] Deleting Composer prompts makes “how we built slice N” harder without git → Acceptable; live contract is code + canonical docs.**

## Migration Plan

1. Merge unique content into keep-set files (`observe.md`, `ai.md`, `goal.md`, `diagrams.md`, `blueprint8.md` link table).
2. Rewrite README, canonical related-doc tables, `openspec/config.yaml`, and remaining keep-set links.
3. Delete the retire-set (proposal file list).
4. Grep for leftover pointers (including `src/docs/`) and fix.
5. Rollback: restore deleted files from git if a unique fact was dropped; this is docs-only.

## Open Questions

None. qs* keep vs merge is a design-level keep (decision 6), not deferred.
