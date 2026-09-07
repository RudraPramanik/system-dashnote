## Why

Blueprint8 Tier 1 (HITL, Langfuse retrieval depth, agent trajectory goldens, fixture CI, failure-mode notes) is the ahead-of-most differentiator, but VPS production proof (A4/A7) is deferred. Local API + FE already run, C-gate goldens exist, and the locked docs already allow an **AI-depth-first** alternate—so we can ship production-ready Tier 1 deepeners against local Compose now without claiming hire-ready or production-live.

## What Changes

- Implement **API-first HITL** on `/ai/agent*`: interrupt before `create_note` / `update_note` side effects; SSE `approval_required`; resume/reject with workspace ownership checks; script + automated tests (no polished FE console required).
- Add **≥5 agent trajectory goldens** (incl. forbid surprise create) to the existing `evals/` harness; keep retrieval/tenant C-gate intact.
- Wire **deterministic fixture evals** into PR CI (no live LLM keys); keep thin CI Alive.
- Deepen **Langfuse traces** with retrieved chunk/note identities + scores (via `observability.tracing` only—no Langfuse SDK inside `src/ai/*`).
- Document **failure-mode notes** and a **local cost/latency sample table** path (README/runbook fields) without requiring HTTPS prod.
- Explicitly treat this work as **local AI-depth-first Tier 1**: Alive on local; forbid production-live / job-search claims until A-gate smoke later.

## Capabilities

### New Capabilities

- `agent-hitl`: Human approval before agent note mutation side effects—interrupt, SSE contract, resume/reject APIs, tenancy, tests/scripts.
- `observability-langfuse`: Retrieval-depth Langfuse enrichment (retrieved chunk/note ids + scores on traces/scores) via the existing observability layer only.

### Modified Capabilities

- `ai-eval-harness`: Require agent trajectory goldens (≥5, tools/sequence constraints) and fixture-mode support suitable for CI; do not replace the C-gate JSONL harness.
- `thin-ci`: Require a PR CI step that runs fixture evals without live LLM/prod secrets.
- `blueprint8-ship-path`: Require operator docs to record the active **AI-depth-first / local Tier 1** window and forbid production-live claims until A-gate.
- `portfolio-baseline`: Require failure-mode notes + cost/latency table fields fillable from local Langfuse/sample runs (honest “local sample” labeling until prod).

## Impact

- **Code**: `src/ai/workflows/workspace_assistant.py`, `src/ai/tools/note_tools.py`, `src/ai_routes/agent.py`, checkpointer usage, `src/observability/tracing.py` (+ RagService span payloads via tracing helpers), possibly new resume routes under `/ai/agent*`.
- **Evals / CI**: `evals/golden/` trajectory cases, `evals/run_eval.py` trajectory assertions, `.github/workflows/ci.yml` fixture-eval job.
- **Docs**: `goal.md` Tier 1 trackers, `slice8_hitl` alignment, runbook failure modes, README cost/latency placeholders marked local until VPS.
- **Constraints**: `docs/documentation/rules.md` laws (imports, service-layer tools, no `src.` imports); chat≠agent; no new `pending_actions` table; no GraphRAG/multi-agent; no polished Next.js HITL UI in this change; sibling FE may later consume `approval_required` but is out of scope here.
- **Out of scope**: VPS TLS/smoke (A4/A7), FE deploy (B7), claiming hire-ready, Langfuse-native experiments replacing goldens, RAGAS/DeepEval, GraphRAG.
