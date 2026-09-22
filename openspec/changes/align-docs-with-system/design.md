## Context

See `proposal.md` for why. Source of truth for the mounted surface is `src/main.py` (`register_routes`), not older architecture prose.

`system.md` was last refreshed for auto-titles, HITL, inbound, and Compose. After that, L3 closed: `POST /ai/feedback` is mounted, `dashnote_ai_*` counters exist, Langfuse host alias works. `observe.md` and `evals/README.md` already describe that path. The hub, LLD, `ai.md` router law, `openspec/config.yaml`, and `frontendguide.md` do not.

In-flight `consolidate-docs` still owns deletions and collapsing dual observe guides. This design only edits keep-set content.

## Goals / Non-Goals

**Goals:**

- Make `system.md` match `register_routes` plus current metrics/eval pointers, then copy that HTTP surface into siblings that duplicate it.
- Keep production-honesty already in the hub (HTTP-IP ≠ A7 HTTPS).
- Keep feedback JWT `wid` only in every copy of the contract.

**Non-Goals:**

- Do not rewrite `observe.md` (already current) except a light cross-link if the hub needs it.
- Do not implement feedback UI, TLS, or application code.
- Do not merge or delete files reserved for `consolidate-docs`.
- Do not expand BLUEPRINT beyond status/placement lines (no new goldens, no judge-on-request).

## Decisions

### 1. Hub first, then siblings

**Choice:** Edit `system.md` against `src/main.py`, then patch `ai.md`, `lld.md`, `openspec/config.yaml`, `frontendguide.md`, and README only where they restate the HTTP surface.

**Why:** Previous `update-system-docs` updated the hub and a subset of siblings; L3 then landed in observe/evals only. Repeating hub-first prevents a second split brain.

**Alternative:** Point every sibling at `system.md` and omit route lists. Rejected for `ai.md` / `config.yaml` / frontend guide — agents copy those lists without opening the hub.

### 2. Summarize L3 on the hub; leave depth in observe + evals

**Choice:** `system.md` Observability gets: traces via `observability.tracing`, `POST /ai/feedback`, `dashnote_api_*` + `dashnote_ai_*`, pointer to `evals/BLUEPRINT.md` with L0–L3 implemented, “not a production SLO / not the hard gate.” Detail stays in `observe.md` and `evals/README.md`.

**Why:** The hub is a map. Duplicating Langfuse env tables will drift again.

**Alternative:** Inline the full L3 procedure into `system.md`. Rejected as a second observe.md.

### 3. BLUEPRINT status-only

**Choice:** Change `evals/BLUEPRINT.md` lines that still say L3 is “this phase” / “current implementation phase” to **done**, keep later phases (thresholds, generator, agent answer goldens) as later. Do not rewrite the four-layer table except the L3 status cell.

**Why:** Spec requires the eval map the hub points at to agree. Full BLUEPRINT rewrite is out of scope.

### 4. Frontend feedback is documented, not gated

**Choice:** Add a short optional subsection under AI APIs in `frontendguide.md`. B-gate checklist unchanged.

**Why:** Matches `frontend-developer-guide` delta. Sibling `dashnotes` is out of this apply root.

### 5. Leave `consolidate-docs` alone

**Choice:** Keep `observability.md` links. Do not delete slice files.

**Why:** Two in-flight doc changes. Content sync vs tree shrink must not collide.

## Risks / Trade-offs

- **[Risk] Hub grows into a third observe.md** → Mitigation: one paragraph + links; no env tables.
- **[Risk] `consolidate-docs` later deletes paths this change links** → Mitigation: only add links to keep-set / evals paths that consolidate-docs also keeps (`observe.md`, `evals/*`). Do not add new links to the retire-set.
- **[Risk] README “built capabilities” overclaims production** → Mitigation: if README lists `/ai` routes, add feedback without marking A7/TLS done.
- **[Risk] Docs-only apply has no pytest** → Mitigation: grep/read validation in tasks (router table vs `main.py`, no “this phase” on L3).

## Migration Plan

Docs-only. No deploy. Rollback is git revert of markdown / `openspec/config.yaml`. Apply after review; do not start in the same turn as this proposal.

## Open Questions

None that affect specs or task breakdown. `dashnotes` UI for thumbs stays a later frontend change.
