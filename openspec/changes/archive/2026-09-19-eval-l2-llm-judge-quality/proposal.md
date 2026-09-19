## Why

L0 fixture-gate and L1 live contract are closed. The next eval layer is **L2 LLM-as-judge quality**: frozen RAG answer goldens scored by DeepEval GEval (correctness, completeness, style) against real `POST /ai/chat` answers. Without L2, operators can prove retrieval markers live but cannot measure answer quality before promote. Gemini free-tier **429** still blocks product chat/embed during collection unless operators pin NVIDIA NIM (different free/catalog model) via the product candidate list — the same hatch L1 already documents.

## What Changes

- Ship **L2 as the third eval implementation phase**: `evals/golden/rag_answers.jsonl` (≈10–20 AI-drafted then curated cases), `evals/run_quality.py`, `evals/requirements-quality.txt` (DeepEval extra, laptop only).
- **Align L2 with L1**: same JWT `wid` tenancy, same seed / marker ID law (reuse retrieval golden seeds where possible), same Compose/staging target and NIM Gemini-429 hatch for the **product** stack that generates answers. L2 does not replace L1; it collects chat answers on top of a proven live contract.
- DeepEval GEval metrics: correctness + completeness as hard floors (example 0.7, tunable later); style always reported (loose / no floor at first). Fail closed on missing judge key, `n=0`, or all-NaN required metrics. Dedicated judge key `GEMINI_API_KEY_2` — never fall back to product `GEMINI_API_KEY`.
- Operator docs: how to run L2, L1/L2 alignment, PR CI stays L0-only, NIM hatch when product chat/embed hits 429, honesty fields (`lab` / `pre-deploy`, judge model, `n`, SKIPs, NaN notes).
- **Mandatory apply validation**: install quality extra, run against a reachable stack with judge key, record actual aggregates (or honest fail-closed outcome). Do not claim L2 works from docs alone. If Gemini 429 blocks product collection, switch to a different NIM free model, recreate `api` + `worker`, re-run.
- Do **not** implement agent answer goldens, threshold/baseline EXPERIMENTS phase, generator prompt rewrites, or a nightly GitHub Actions judge workflow. Do **not** import DeepEval from `run_eval.py`. Do **not** put the judge on `/ai/chat` or `/ai/agent`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-eval-harness`: L2 quality CLI is a first-class operator/pre-deploy suite — RAG answer goldens, DeepEval GEval metrics, fail-closed honesty, L1-aligned live collection + NIM hatch for product 429, apply MUST prove a real run.
- `eval-lifecycle`: Third follow-on after L0/L1 is L2 judge quality. Blueprint roadmap/README MUST mark L2 as this phase (thresholds / agent answers remain later); L1/L2 alignment and NIM hatch for collection MUST be documented; PR CI stays fixture-only.

## Impact

- **Eval:** New `evals/run_quality.py`, `evals/requirements-quality.txt`, `evals/golden/rag_answers.jsonl`; updates to `evals/README.md`, `evals/BLUEPRINT.md`. Optional CI-safe unit tests under `tests/evals/` for fail-closed helpers only (no live HTTP, no DeepEval network in pytest).
- **Judge:** Operator laptop uses `GEMINI_API_KEY_2` (+ DeepEval). Product chat/embed still uses existing `LLM_MODEL` / `LLM_MODEL_FALLBACKS` (NIM before Gemini Flash). Judge suite MUST NOT land in API/worker images or Compose serving deps.
- **CI:** Unchanged — fixture-only in `.github/workflows/ci.yml`. L2 remains local / pre-deploy / nightly (manual), not a merge gate.
- **Tenancy:** Unchanged. JWT `wid` only on `POST /ai/chat`; tenant-isolation goldens remain the C-gate proof.
- **Non-goals:** No agent_answers.jsonl, no collapsing chat/agent, no judge on the hot path, no L2 as PR merge gate, no treating GEval means as production SLOs, no retiring RAGAS/Langfuse labs in this change.
- **Apply gate:** Implementation is not complete until `run_quality.py` is run against a real base URL with JWT + judge key and the actual per-metric aggregates / `n` / SKIPs (or honest fail-closed exit) are recorded in `evals/README.md` (and optionally a dated `lab` / `pre-deploy` note). If Gemini 429 blocks product collection, apply MUST switch to a different NIM free model and re-validate — not invent scores.
