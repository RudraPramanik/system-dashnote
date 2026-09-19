## Why

L0 fixture-gate, L1 live contract, and L2 LLM-as-judge quality are closed as separate eval phases. The next layer in `evals/BLUEPRINT.md` is **L3 production observability**: Langfuse traces, Prometheus health, and `POST /ai/feedback`. Serving pieces already exist, but the eval program has not closed L3 as an implementation phase: the blueprint still treats L3 as an unlabeled “exists” box, L0/L1 alignment is not re-proven on this apply, L2/L3 placement is not a named contract, and production-shaped env uses `LANGFUSE_BASE_URL` while the API reads `LANGFUSE_HOST` — so keys already present in `.env.production` can sit unused. Without an L3 apply that actually emits traces, records feedback, and re-checks L0/L1, later promote work would claim observability while CI contract and live tenancy drift.

## What Changes

- Close **L3 as the fourth eval implementation phase** after L2: production-serving traces (`rag.answer` / `agent.turn`), low-cardinality Prometheus quality counters, and JWT `POST /ai/feedback` (thumbs or 1–5). Langfuse remains soft; `/ai/chat` and `/ai/agent` MUST NOT await a judge.
- **Keep L0 aligned with L1**: same `evals/golden/` corpus, same marker / isolation / trajectory scorers, fixtures as the recorded form of the live contract. Apply MUST re-run fixture mode and confirm the shared-scoring contract still holds before claiming L3 works.
- **Align L3 with L0/L1/L2**: L3 uses the same JWT `wid` tenancy as L1/L2 for traces and feedback; L3 MUST NOT replace L0/L1 `PASS: X/Y` or L2 GEval; PR CI stays L0 fixture-only; L2 stays off the hot path; sampled Langfuse faithfulness remains operator/nightly (`evals/run_langfuse_faithfulness.py`).
- **Production env wiring**: Settings MUST honor the documented `LANGFUSE_HOST` and accept a `LANGFUSE_BASE_URL` alias so existing production keys enable the client. Docs MUST name key vars only — never commit or paste secrets from `.env.production`.
- Operator docs: how to confirm traces in Langfuse UI, submit feedback, scrape `/metrics`, and that L3 is serving observability — not a merge gate and not a production SLO.
- **Mandatory apply validation**: with Langfuse keys already available to the operator (`.env.production` / local `.env`), prove a real chat or agent turn produces a trace, `POST /ai/feedback` returns 2xx, and Prometheus still exposes `dashnote_ai_*` counters. Re-run L0 fixture and record honest `PASS: X/Y`. Prefer a stack already proven by L1. Do not invent traces or scores.
- Do **not** add GEval/RAGAS to the request path, API image, or VPS serving deps. Do **not** implement thresholds/baseline, generator prompt rewrites, agent answer goldens, or a PR-blocking judge workflow.

## Capabilities

### New Capabilities

- `ai-feedback`: Authenticated `POST /ai/feedback` attaches a user thumbs or 1–5 signal to the current AI turn’s Langfuse trace (JWT `wid` only; 2xx `tracing=unavailable` when Langfuse is off).

### Modified Capabilities

- `eval-lifecycle`: Fourth follow-on after L0/L1/L2 is L3 production observability. Blueprint/README MUST mark L3 as this phase, keep L0/L1 alignment language, add L2/L3 placement (observability never replaces contract or GEval; never await a judge on chat/agent), and leave thresholds / generator / agent answers as later phases.
- `ai-eval-harness`: L3 is a first-class serving-observability layer on the eval map — operator docs for Langfuse UI + feedback + Prom, apply MUST re-validate L0 fixture (and L0/L1 shared-scoring alignment) and prove a real trace/feedback path. Fixture CI stays keyless and Langfuse-free.
- `observability-langfuse`: Production-shaped env enables the existing lazy client (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` + host, with `LANGFUSE_BASE_URL` alias). Tracing and scores stay soft; empty-retrieval and user-feedback scores remain Langfuse-side, not Prometheus judge series.

## Impact

- **Eval / docs:** `evals/BLUEPRINT.md`, `evals/README.md`, and observe/EXPERIMENTS pointers. Roadmap inserts L3 close-out after L2; L0/L1 alignment section stays required. No new golden corpus. No DeepEval on the VPS.
- **Serving:** Existing `observability.tracing`, `POST /ai/feedback`, and `dashnote_ai_*` counters. Config/env alias so production keys actually enable Langfuse. No **BREAKING** chat/agent/HITL/health contracts.
- **CI:** Unchanged — `.github/workflows/ci.yml` stays L0 fixture-only with no Langfuse or judge keys.
- **Tenancy:** Unchanged. Trace metadata and feedback authorize by JWT `wid` only.
- **Secrets:** Apply uses keys already in operator `.env.production` / `.env`. Artifacts and README MUST use placeholders only.
- **Non-goals:** No GEval on `/ai/chat` or `/ai/agent`, no L3 as PR merge gate, no treating traces or thumbs as production SLOs, no L2 threshold/generator/agent-answer work in this change.
- **Apply gate:** Implementation is not complete until (1) L0 fixture is re-run and recorded, (2) L0/L1 alignment is confirmed (shared goldens/scorers still documented and fixture still green), and (3) a real Langfuse-enabled turn plus `POST /ai/feedback` is proven — not claimed from older observe.md text.
