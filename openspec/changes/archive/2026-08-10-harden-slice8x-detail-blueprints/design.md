## Context

Three detail blueprints (`slice8_ci.md`, `slice8_eval.md`, `slice8_hitl.md`) already exist and are indexed from `slice8_X.md`. A review (`new.md`) proposed fixes; exploration against the repo showed:

- Dockerfile is **`python:3.12-slim`** (not 3.11) — the review’s “never 3.12” rewrite is inverted.
- Tests largely use sqlite/fakes; service containers are an inventory question, not a default law.
- `pytest.ini` already sets `pythonpath = src`; explicit CI `PYTHONPATH` is hygiene, not panic.
- Eval blueprint lacks machine-checkable schema/modes/seed strategy.
- HITL blueprint underspecifies resume tenancy, SSE lifecycle, and interrupt API version discipline; critic conflated automation pending actions with LangGraph checkpointer state.

This change edits blueprints + OpenSpec specs only.

## Goals / Non-Goals

**Goals:**

- Make each detail blueprint safe to paste into Composer without false premises.
- Encode grounded verdicts as architecture laws and substep gates.
- Sync OpenSpec blueprint specs so archive stays coherent.

**Non-Goals:**

- Implementing `.github/workflows/ci.yml`, `evals/`, or HITL code.
- Replacing blueprints with the full `new.md` CI rewrite.
- Changing `Dockerfile` Python version or downgrading to 3.11.
- Adding a `pending_actions` table for agent HITL.
- Rewriting `slice8_X.md` structure (light consistency only if a line contradicts hardened laws).
- Treating `new.md` as canonical.

## Decisions

### D1 — CI Python/apt law = match Dockerfile (not pin 3.11)

- **Choice:** Architecture law: “CI Python version and apt packages MUST match the Dockerfile base image and apt-get layer.” Today that means 3.12 + `libmagic1`.
- **Alternatives:** Force 3.11 forever (rejected — creates mismatch); leave 3.12 only in the skeleton prompt (weaker — agents can still invent 3.x).
- **Rationale:** Inventory reads Dockerfile; laws must not fight ground truth.

### D2 — Service containers after inventory, not by default

- **Choice:** 8X.1.0 must report whether any test path needs live Postgres/Redis. Add services only if needed; do not invent credentials that diverge from `tests/conftest.py` setdefaults.
- **Alternatives:** Always add postgres+redis (review default) — overkill given sqlite/fake patterns.
- **Rationale:** Fewer flaky CI deps; inventory remains the gate.

### D3 — PYTHONPATH as belt-and-suspenders

- **Choice:** Document that `pytest.ini` `pythonpath = src` is primary; CI job MAY/SHOULD also set `PYTHONPATH: src`.
- **Alternatives:** Claim every import fails without env PYTHONPATH (overstated).

### D4 — Eval runner modes + seed/fixture in 8X.2.0

- **Choice:** Schema docs in 8X.2.0 lock: `--mode fixture|live` (names may vary), trajectory fields (`forbidden_tools`, `required_tools`, `sequence_mode: exact|subset`), tenant dual-token or fixture, and seed-or-fixture for entity IDs. PR CI only runs fixture/deterministic subset.
- **Alternatives:** Defer contracts to 8X.2.4 docs-only (rejected — goldens written in 8X.2.1 would be unrunnable).

### D5 — HITL: checkpointer is pending state; SSE close-then-resume

- **Choice:** Pending mutation interrupt state lives in the existing LangGraph checkpointer. Prefer SSE contract: emit `approval_required` then close stream; client reconnects/calls resume with same `thread_id`. Resume MUST verify thread/checkpoint belongs to caller’s workspace. Lock event JSON fields. Require reading installed LangGraph version before choosing `interrupt()` vs legacy API; tighten pin when implementing.
- **Alternatives:** Keep SSE open during wait (harder with proxies); mandatory `pending_actions` table (wrong surface for this gate); leave event shape “align somehow.”
- **Rationale:** Matches existing agent stream end pattern (`done` + `[DONE]`); separates Slice 7 automation queue from agent HITL.

### D6 — Additional blueprint polish beyond the review

- CI failure-category playbook (import / apt / Settings / DB) in 8X.1.2 — useful without adopting wrong env examples.
- Eval README must document how to invoke runner with `src` on path.
- HITL: document event order relative to `tool_start`/`tool_end`.
- Cross-file: readiness tables should cite concrete code anchors already present (`agent.py` event types, `conftest.py`, Dockerfile).

## Risks / Trade-offs

- [Risk] Future Dockerfile Python bump orphans blueprint text → Mitigation: law is “match Dockerfile,” not a hardcoded version forever; inventory flags drift.
- [Risk] Fixture-mode evals under-test live RAG quality → Mitigation: honest docs; live/nightly path remains; C-gate can still require operator live run.
- [Risk] Close-then-resume SSE differs from some LangGraph demos that keep the connection → Mitigation: document explicitly; FE later can follow the same contract.
- [Risk] Over-specifying trajectory schema before runner exists → Mitigation: schema is blueprint contract; implementer may extend fields but MUST NOT drop required ones.

## Migration Plan

1. Edit the three detail markdown files in place (preserve substep numbering and parent links).
2. Apply OpenSpec delta specs to main specs on archive/sync.
3. Leave `new.md` as historical review notes or later delete/archive out of band — not part of apply gate.
4. Rollback: git revert the doc commits; no runtime migration.

## Open Questions

- Exact CLI flag names (`--mode` vs `--fixture`) — leave to implementer when coding 8X.2.2; blueprint states the two modes must exist.
- Whether to pin `langgraph` lower bound in requirements during 8X.3.1 or only document “read installed version” until first green HITL — prefer document-now, pin-when-implementing.
