## Context

Option **B** was chosen: keep `slice8_X.md` as the ship-path index, and put agent-executable detail in three empty files the user created:

- `docs/documentation/blueprint/slice8_ci.md`
- `docs/documentation/blueprint/slice8_eval.md`
- `docs/documentation/blueprint/slice8_hitl.md`

`slice8_X.md` already defines order (CI → evals → HITL → finish prod → FE), laws, and the pre-7P.8 exception, but 8X.1–8X.3 are still single-shot prompts. Slice 6/7 show the target density: readiness → ARCHITECTURE LAW → numbered substages with NEW FILES / NEVER TOUCH → file-level TASK blocks → validation gate → fallbacks.

This change fills the three detail blueprints and slims `slice8_X.md` to TOC + pointers. **Docs only.**

## Goals / Non-Goals

**Goals:**

- Slice-6-grade substages for CI, evals, and HITL (one Composer session ≈ one substep).
- Shared patterns: paste-first laws, explicit never-touch lists, gates, fallbacks if inventory fails.
- `slice8_X.md` remains the single entry point; detail files are linked for 8X.1–8X.3.
- 8X.4 stays a pointer to `slice-platform.md` (no forked 7P.4–7P.8 prompts). 8X.5 stays a pointer to `frontendguide.md` / B-gate.

**Non-Goals:**

- Implementing `.github/workflows/ci.yml`, `evals/`, or HITL runtime code.
- Expanding 8X.4 into a duplicate platform blueprint.
- GraphRAG / multi-agent productization.
- Archiving the prior `slice8x-ci-evals-hitl-blueprint` change (optional follow-up).

## Decisions

### D1 — File layout (option B)

| File | Role |
|------|------|
| `slice8_X.md` | TOC, global 8X law, path order, pre-7P.8 exception, links |
| `slice8_ci.md` | 8X.1 substages |
| `slice8_eval.md` | 8X.2 substages |
| `slice8_hitl.md` | 8X.3 substages |

### D2 — CI substages (`slice8_ci.md`)

```
8X.1.0  Inventory — conftest, pytest.ini, requirements path, local pytest baseline
8X.1.1  Workflow skeleton — ci.yml triggers + job stubs; no secrets
8X.1.2  Test job green — env aligned to fixtures; fix only CI-blocking gaps
8X.1.3  Docker build job + gate — needs: test; mark production.md 7P.7
```

Reuse intent from `slice-platform.md` §7P.7 but expand to multi-gate. Do not require live LLM/Qdrant for green CI.

### D3 — Eval substages (`slice8_eval.md`)

```
8X.2.0  Schema + folder laws — JSONL contract; evals/golden/; no live LLM in PR
8X.2.1  Retrieval + tenant isolation goldens (≥10 theme coverage)
8X.2.2  Runner CLI for those cases (PASS: X/Y)
8X.2.3  Agent trajectories ≥5 (incl. forbid surprise create)
8X.2.4  Optional deterministic CI wire + honest pass-rate docs
```

Align with `ai-eval-harness` + agent extension from `slice8_X.md`.

### D4 — HITL substages (`slice8_hitl.md`)

```
8X.3.1  Interrupt before create_note / update_note (graph; chat untouched)
8X.3.2  SSE approval_required (align with ai_routes/agent.py stream types)
8X.3.3  Resume-by-thread_id / checkpointer
8X.3.4  Curl/script smoke + tests — FE approval UI forbidden for gate
```

### D5 — Document shape per detail file

Mirror Slice 6/7:

1. Title + when-to-run + link back to `slice8_X.md`
2. Readiness gate
3. ARCHITECTURE LAW (paste-first; domain-specific)
4. Sub-steps with OBJECTIVE prompt, TASK list (file-level where known), GATE
5. Fallback / out-of-scope table
6. “Complete — what was built” checklist

Where exact code is not yet known, prompts MUST say “read X first; invent minimally” rather than hallucinate APIs — same spirit as Slice 6’s grounded paths.

### D6 — Slimming `slice8_X.md`

Replace long 8X.1–8X.3 embedded OBJECTIVE blocks with short summaries + “Full prompts: `slice8_*.md`”. Keep overview ASCII, global law, exception table, 8X.4/8X.5 pointers, status tracker.

### D7 — Fallbacks (architecture solidity)

Each detail blueprint MUST include fallbacks such as:

- Local pytest red → fix or document skip before CI invents env hacks
- Requirements path unclear → inventory substep stops and reports
- Agent stream event names differ → HITL implements after reading `agent.py`; proposed name is default
- Live eval flakes → never block PR CI; nightly/operator only

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Drift between `slice8_X` and detail files | TOC is source of order; detail owns prompts; apply tasks include consistency skim |
| Overlong prompts (agent context) | Split files already; keep each substep to one session |
| Duplicate of slice-platform 7P.7 | CI file expands; still references platform for topology laws |
| Prior complete change not archived | Harmless; optional archive later |

## Migration Plan

1. Write three detail blueprints.
2. Slim `slice8_X.md` TOC links.
3. Touch cross-links if filenames need explicit mention.
4. No runtime deploy; rollback = revert docs.

## Open Questions

- Whether CI inventory requires a committed “known failing tests” allowlist — leave to 8X.1.0 verdict in the blueprint.
- Exact resume HTTP shape (new route vs same stream) — HITL blueprint proposes options; implement change chooses after reading graph APIs.
