## Context

See `proposal.md` for why. Current state: golden evals + CI exist (`evals/`); Langfuse records tokens/cost on RAG traces when enabled; README cost/latency is still **pending fill**; no EXPERIMENTS before/after file; talk track covers fixture vs live but does not name the Eval Paradox; file parse→index pipeline is real but lacks a single “messy data” demo fixture/diagram for interviews.

This change is evidence-and-docs first. Prefer documenting existing behavior over new runtime platforms.

## Goals / Non-Goals

**Goals:**
- Fill D4 with honest local/sample cost+latency and one optimization comparison.
- Ship EXPERIMENTS with ≥1 reduce-error / quality loop tied to the harness.
- Package Eval Paradox into the talk track.
- Add a light messy-data fixture + pipeline diagram for interview demos.

**Non-Goals:**
- `ai_usage` metering API, billing dashboards, production SLOs from local samples.
- RAGAS / faithfulness as CI gates; recall@k hire gates.
- OCR, hybrid search, GraphRAG, multi-agent expansion.
- Replacing fixture CI with live LLM judges.

## Decisions

### 1. EXPERIMENTS lives at `docs/EXPERIMENTS.md` (link from `evals/README.md` + README)
- **Why:** Portfolio/interview readers start at docs and README; eval operators start at `evals/`. One canonical file avoids drift.
- **Alternatives:** Only under `evals/` (harder for README strangers); only Langfuse UI notes (not in-repo proof).

### 2. Cost sample uses existing Langfuse `llm_generation` fields when keys available; else scripted token/latency from a fixed `/ai/chat` set
- **Why:** Observe.md already documents token/cost on spans; no new SDK path. If Langfuse unavailable, a small manual table from response `latency_ms` + provider usage still satisfies “local/sample.”
- **Alternatives:** Build `ai_usage` API (deferred in goal.md); invent mock dollars without a run (rejected — dishonest).

### 3. Smallest ROI optimization story: document *existing* controls with a measured delta where possible
Preferred order (pick first that yields a measurable before/after without product risk):
1. Embedding cache hit vs cold embed on identical text (tokens/$ for embed path).
2. Empty-retrieval skip (0 generation tokens vs forced call) — narrative + trace proof.
3. Optional one-knob sample: temporarily tighter `TOKEN_BUDGET_PER_REQUEST` on a fixed query set, record tokens, restore default — document as lab sample only.
- **Why:** Avoid shipping permanent quality regressions just for a portfolio number.
- **Alternatives:** Swap chat model globally (noisy); claim caps without measurement (weak).

### 4. Reduce-error experiment: prefer a harness-visible loop
- Prefer: add/adjust 1 golden or fixture that fails on a known bad behavior → fix or document already-fixed path → `PASS: X/Y` before/after.
- Acceptable alternate: document a historical fix already in tree (empty-retrieval honest fallback, citation grounding) with fixture case proving the regression gate — as long as baseline vs after is explicit.
- **Why:** Interviewers want “we measured error rate and reduced it,” not only green CI.

### 5. Messy-data slice stays documentary + one fixture
- Edge PDF or intentionally empty/corrupt extract case under tests/evals fixtures; ASCII/mermaid pipeline in `docs/documentation/` (ai.md or a short linked snippet).
- **Why:** Pipeline already exists; horror-story proof ≠ building OCR.

### 6. Tracker updates are part of apply
- Mark D4 complete in `goal.md` only after the table is filled; link EXPERIMENTS from portfolio signals.

## Risks / Trade-offs

- **[Risk] Local cost numbers mistaken for prod SLOs** → Mitigation: mandatory `local/sample` labels; README already forbids unverified production claims.
- **[Risk] Optimization run harms quality** → Mitigation: prefer cache/empty-retrieval evidence; if budget knob used, restore defaults and label as lab.
- **[Risk] Fake EXPERIMENTS without a real measurement** → Mitigation: require `PASS: X/Y` or golden case id + date/environment.
- **[Risk] Scope creep into metering API / RAGAS** → Mitigation: non-goals; tasks stay doc+one sample+one loop+one fixture.
- **[Trade-off] Optional messy fixture may be skippable if time-boxed** → Spec still requires discoverability; implement with smallest fixture (even empty-extract path) rather than deferring forever.

## Migration Plan

1. Write EXPERIMENTS + talk-track updates (no runtime deploy).
2. Run local cost sample (Compose + optional Langfuse) → fill README.
3. Run/record eval before/after for the chosen loop → update EXPERIMENTS + evals README links.
4. Add messy fixture + diagram; link from README or ai docs.
5. Update `goal.md` D4 / related checkboxes.
6. No DB/migration/rollback — docs-only revert if needed.

## Open Questions

None blocking. Operator may choose Langfuse vs scripted cost capture at apply time based on whether keys are configured.
