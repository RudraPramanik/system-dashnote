## 1. L0 scoring tests

- [x] 1.1 Add CI-safe `tests/evals/test_run_eval.py` that imports scoring helpers from `evals/run_eval.py` (same `sys.path` pattern as `test_ragas_lab.py`) with no live HTTP
- [x] 1.2 Cover retrieval marker miss, tenant leaked `expect_no_content_markers`, and trajectory forbidden `create_note` as fail cases; include at least one happy-path pass each
- [x] 1.3 Run `python -m pytest tests/evals/test_run_eval.py -q` and confirm it passes without Gemini or NVIDIA keys

## 2. Rate-limit candidate walk

- [x] 2.1 Add `is_rate_limited` in `src/shared/llm/fallback.py` (HTTP 429, LiteLLM `RateLimitError`, quota/rate-limit text) without treating it as model-gone in logs
- [x] 2.2 After per-candidate retry exhaustion, walk to the next `LLM_MODEL` / `LLM_MODEL_FALLBACKS` id, skip the rate-limited id for the process, and increment the existing fallback metric
- [x] 2.3 Extend `tests/shared/test_llm_fallback.py`: 429 then later NIM success; subsequent call does not start on the 429 id; all-429 raises `LLMUnavailableError`
- [x] 2.4 Run `python -m pytest tests/shared/test_llm_fallback.py -q`

## 3. Second NVIDIA NIM fallback

- [x] 3.1 Ping 1–3 small NVIDIA NIM ids that are not the Lightning primary and not Super 120B / Ultra 550B via `scripts/test_nvidia_nim.py` (or equivalent); do not commit API keys
- [x] 3.2 Put the first entitled id into documented `LLM_MODEL_FALLBACKS` **before** `gemini/gemini-2.5-flash` in `.env.example` and `src/config.py` defaults; if none entitled, keep Gemini last and comment the operator-chosen NIM hop — do not invent a verified-dead id
- [x] 3.3 Update `docs/documentation/ai.md` candidate table to match; if local `.env` is changed, recreate `api` + `worker` — do not commit secrets

## 4. Operator docs

- [x] 4.1 Update `evals/README.md` layout (BLUEPRINT, trajectory goldens) and state L0 fixture needs no Gemini/NIM keys; name NVIDIA NIM (different free model) as the Gemini 429 hatch for later live layers
- [x] 4.2 Patch `evals/BLUEPRINT.md` phased roadmap so L0 close-out is the first implementation phase after the blueprint, DeepEval stays later, and the NIM 429 hatch is documented without putting a judge on `/ai/chat` or `/ai/agent`

## 5. Validate L0 works

- [x] 5.1 From repo root run `$env:PYTHONPATH = "src"; python evals/run_eval.py --mode fixture` with no live keys; apply fails if the process exits non-zero
- [x] 5.2 Record the actual `PASS: X/Y` and date in `evals/README.md` latest-run table; do not copy the 2026-09-07 row
- [x] 5.3 Confirm `.github/workflows/ci.yml` still runs only `--mode fixture` and that this change did not add `run_quality.py`, `rag_answers.jsonl`, or DeepEval deps
