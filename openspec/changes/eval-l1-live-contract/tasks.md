## 1. Docs and L0/L1 alignment

- [x] 1.1 Update `evals/BLUEPRINT.md` phased roadmap: mark L0 done; insert **L1 live contract** as the next phase; shift DeepEval / `run_quality.py` after L1; document L0/L1 shared goldens + scoring (fixtures = recorded contract)
- [x] 1.2 Update `evals/README.md`: L1 live procedure (`--mode live`, `--base-url`, `--token`, `--token-b`, `--seed-live`), L0/L1 alignment note, PR CI stays fixture-only, NVIDIA NIM (different free/catalog model) hatch when Gemini 429 blocks the live stack
- [x] 1.3 Confirm golden `mode_hint` / `skip_if_modes` / `seed` fields match the L1 eligibility law (fixture-only vs either/live); adjust only if a case is mis-labeled for live — do not invent answer goldens

## 2. Live runner hardening

- [x] 2.1 Harden `evals/run_eval.py` live path: clear SKIP reasons (fixture-only, missing `--token-b`, unwired live trajectory), never score `actor=b` with only `--token`, keep shared `score_case` / payload normalize for retrieval and tenant themes
- [x] 2.2 Ensure live summary prints environment-friendly honesty fields operators need (scored PASS/FAIL ids, SKIP count); exit non-zero on any scored FAIL; do not treat all-SKIP as success for apply
- [x] 2.3 Add or extend CI-safe unit tests under `tests/evals/` for live eligibility / SKIP helper behavior only (no live HTTP, no LLM keys) if 2.1 introduces testable branches

## 3. Apply validation (must prove it works)

- [x] 3.1 Run L0 alignment check from repo root: `$env:PYTHONPATH = "src"; python evals/run_eval.py --mode fixture` — confirm still green (or record honest fixture `PASS: X/Y` if not)
- [x] 3.2 Bring up local Compose (or use a reachable staging URL); verify `GET /health` and `GET /health/ai`; obtain JWT `--token` (and `--token-b` when validating member deny)
- [x] 3.3 Run L1: `python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token "<jwt>" --seed-live` (add `--token-b` when available). If Gemini **429** / quota blocks embed or product LLM paths, switch to a different NVIDIA NIM free/catalog model via `LLM_MODEL` / `LLM_MODEL_FALLBACKS`, recreate `api` + `worker`, and re-run — do not invent scores
- [x] 3.4 Record the actual live `PASS: X/Y`, SKIP count/reasons, environment `live-local` (or staging), and date in `evals/README.md`. Apply is incomplete if zero cases were scored or if scored failures remain unexplained. Do not reuse the 2026-09-06 live row as proof
- [x] 3.5 Confirm `.github/workflows/ci.yml` still runs fixture-only (no live token, no judge, no L1 merge gate)
