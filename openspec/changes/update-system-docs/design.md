## Context

See `proposal.md` for why. Spec delta: `canonical-docs` (ADDED requirements only; prior Sept 9 requirements remain in force).

Constraints:

- Source of truth for HTTP remains `register_routes()` in `src/main.py`. Auto-title and `PATCH /ai/threads/{thread_id}` already exist in code; this change documents them.
- Source of truth for local stack remains `docker-compose.yml`. Prod thin stack remains `docker-compose.prod.yml` + hosted deps via `.env`.
- Deep inbound ops stay in `docs/inbound-channels.md`. Production first-boot narrative stays in `docs/deployment/runbook.md` / `docs/documentation/production.md` / `docs/devops-progress.md` — `system.md` links, does not fork.
- Docs-only: no API, worker, Nginx, Alembic, or compose file edits.

## Goals / Non-Goals

**Goals:**

- Bring `system.md` current for threads/auto-titles, testing commands, and prod/ops pointers.
- Keep `ai.md` and `lld.md` coherent with the same auto-title contract.
- Refresh `openspec/config.yaml` context so future agents see PATCH threads, auto-title, and devops-progress in the canonical list.
- Fix stale Phase 1 / current-level wording in `docs/devops-progress.md` against `goal.md`.

**Non-Goals:**

- Rewriting `qs.md` / blueprints, expanding inbound into `system.md`, changing `frontendguide.md` beyond an optional smoke link, or implementing code.

## Decisions

### D1 — Edit in place; do not rewrite `system.md` from scratch

Patch the existing Sept 9 structure: router row for threads, a short **Conversation auto-titles** subsection (or AI features bullet), testing commands, and Docker Compose prod cross-links. Preserve accurate sections (health, middleware, lifespan, integrations summary, Grafana-not-in-compose).

**Alternative considered:** Full rewrite of `system.md` — rejected; most of the file still matches code and would create unnecessary review noise.

### D2 — Auto-title detail lives in `ai.md`; `system.md` stays a map

`system.md` gets a concise summary + link to `smoke-conversation-titles.md` and `ai.md`. `ai.md` owns one-shot rules, SSE `title`, and thread rename contract. `lld.md` gets a short sequence note only where thread/chat flows are already described.

**Alternative considered:** Duplicate the full auto-title design into `system.md` — rejected; keeps the map bloated and drifts faster.

### D3 — Production detail stays in ops docs; `system.md` links

Add compose prod notes that are already true in `docker-compose.prod.yml` (`IMAGE=`, api healthcheck, worker depends on healthy api) plus links to devops-progress / runbook / production.md. Do not copy the full first-boot checklist into `system.md`.

**Alternative considered:** Merge runbook into `system.md` — rejected; ops trackers change often and belong outside the architecture map.

### D4 — Sync devops-progress status, not the whole learner guide

Update only contradictory status lines / Phase 1 checkboxes so they match `goal.md` A4 PASS. Leave phase pedagogy and later open items intact.

### D5 — Process ownership

| Work | Owner |
|------|--------|
| Narrative accuracy | `system.md`, `ai.md`, `lld.md` |
| Ops tracker accuracy | `docs/devops-progress.md` |
| Agent prompt accuracy | `openspec/config.yaml` |
| Runtime code | Unchanged |

## Risks / Trade-offs

- **[Risk] Over-documenting auto-title internals → Mitigation:** Behavior + contracts only; point to `smoke-conversation-titles.md` and code paths by module name lightly.
- **[Risk] Ops links rot again → Mitigation:** Prefer stable paths (`devops-progress.md`, `runbook.md`, `production.md`); avoid embedding phase checkbox text in `system.md`.
- **[Risk] Accidental reintroduction of stale claims (POST test-search, Grafana in Compose) → Mitigation:** Verify tasks grep for those anti-patterns after edits.

## Migration Plan

Docs-only merge. No deploy steps. Rollback = revert the doc commits.
