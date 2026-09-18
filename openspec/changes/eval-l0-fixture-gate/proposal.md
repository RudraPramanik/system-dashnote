## Why

The eval lifecycle blueprint is docs-only. The first implementation step is **L0** (deterministic fixture / golden contract), not DeepEval. The fixture runner already exists in CI, but it has no pytest coverage, the operator README still describes a stale layout, and apply of later layers would skip proving L0 actually passes. Live collection has already failed on Gemini free-tier **429** (RAGAS lab chat 500s) because candidate walk currently treats rate-limit as fatal and `LLM_MODEL_FALLBACKS` is only Gemini Flash — operators need NVIDIA NIM with a different free model when Gemini is quota-blocked.

## What Changes

- Close **L0 as the first post-blueprint implementation phase**: CI-safe pytest for fixture scoring (markers, tenant isolation, trajectories), README/BLUEPRINT alignment, and a **mandatory apply validation run** of `python evals/run_eval.py --mode fixture` that records the honest `PASS: X/Y`.
- Keep L0 **keyless**: fixture mode MUST complete with no `GEMINI_API_KEY`, no `GEMINI_API_KEY_2`, and no `NVIDIA_NIM_API_KEY`.
- When a live LLM candidate returns **rate-limit / 429** (Gemini or otherwise), walk to the next `LLM_MODEL` / `LLM_MODEL_FALLBACKS` id. Documented defaults MUST include at least one additional currently-live **NVIDIA NIM** free/catalog model distinct from the primary, then Gemini Flash — not Super 120B / Ultra 550B.
- Do **not** implement L2 (`run_quality.py`, `rag_answers.jsonl`, DeepEval) or make live L1 a PR merge gate.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-eval-harness`: L0 fixture gate is the first eval implementation to close — pytest for scoring, operator docs that L0 needs no LLM keys, and apply MUST prove the fixture runner with a recorded `PASS: X/Y`.
- `eval-lifecycle`: First follow-on after the blueprint is L0 (not L2). Blueprint/README MUST name NVIDIA NIM (different free model) as the Gemini 429 escape hatch for later live layers; L0 itself stays fixture-only.
- `llm-resilience`: Completions MUST walk candidates on provider rate-limit / HTTP 429, not only model-gone (410) and wall-clock timeout. Example fallbacks MUST include another live NVIDIA NIM id so Gemini quota does not pin the process on a dead fallback.

## Impact

- **Eval:** `evals/README.md` (and a short BLUEPRINT L0/quota note). New CI-safe tests under `tests/evals/` for `run_eval.py` scoring. Fixture goldens/fixtures stay; no new answer goldens.
- **LLM:** `src/shared/llm/fallback.py` plus `tests/shared/test_llm_fallback.py`. `.env.example` / `docs/documentation/ai.md` candidate list. Local `.env` is operator-owned — recreate `api` + `worker` after fallbacks change.
- **CI:** Still fixture-only in `.github/workflows/ci.yml`. New pytest files ride the existing pytest step. No judge extras, no live keys.
- **Tenancy:** Unchanged. JWT `wid` remains the live search scope; L0 fixtures do not call the API.
- **Non-goals:** No DeepEval, no `run_quality.py`, no collapsing `/ai/chat*` and `/ai/agent*`, no judge on the hot path, no Super 120B/Ultra 550B as default hops, no treating L0 scores as SLOs.
- **Apply gate:** Implementation is not complete until fixture evals are run locally and the actual summary is recorded. Do not claim L0 works from an old README row.
