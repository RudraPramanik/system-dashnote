## 1. Docs and L1/L2 alignment

- [ ] 1.1 Update `evals/BLUEPRINT.md`: mark L0/L1 done; mark **L2 LLM-as-judge** as this phase; keep thresholds / agent answers / nightly judge workflow as later phases; document L1/L2 alignment (JWT `wid`, seed/marker law, NIM hatch for product 429 during collection); mark `run_quality.py` / `rag_answers.jsonl` / `requirements-quality.txt` as the L2 ship set
- [ ] 1.2 Update `evals/README.md`: L2 install + run procedure (`pip install -r evals/requirements-quality.txt`, `GEMINI_API_KEY_2`, `python evals/run_quality.py --token … --base-url …`), L1/L2 alignment note, PR CI stays fixture-only, NVIDIA NIM (different free/catalog model) hatch when Gemini 429 blocks product chat/embed during collection, honesty fields (`lab`/`pre-deploy`, judge model, `n`, SKIPs)
- [ ] 1.3 Confirm `.env.example` still documents empty `GEMINI_API_KEY_2` as judge/RAGAS-only (not embeddings); do not add judge key to Compose, API Settings, or VPS product env

## 2. Answer goldens

- [ ] 2.1 Author `evals/golden/rag_answers.jsonl` with ~10–20 cases (`id`, `theme=rag_answer`, `surface=POST /ai/chat`, `query_text`, `expected_output`, `completeness_checklist`, optional `style_notes`, `seed` aligned with retrieval markers where possible). Label corpus AI-drafted/curated in README. No hard-coded environment-only note/chunk UUIDs
- [ ] 2.2 Do not add `agent_answers.jsonl` in this change; do not treat trajectory goldens as the L2 answer suite

## 3. Quality CLI and laptop extra

- [ ] 3.1 Add `evals/requirements-quality.txt` (DeepEval + documented pins). Keep it out of API/worker/Compose serving images
- [ ] 3.2 Implement `evals/run_quality.py`: load judge key fail-closed (never fall back to `GEMINI_API_KEY`); load goldens (`--limit` optional); for each case `POST /ai/chat` with JWT; SKIP on non-200 / empty answer / empty retrieval; DeepEval GEval correctness + completeness (hard floor ~0.7) + style (report; loose/no floor); print environment, judge model, aggregates, `n`, SKIPs, NaN notes; exit non-zero on missing key, `n=0`, all-NaN required metrics, or hard-floor miss
- [ ] 3.3 Do not import DeepEval from `evals/run_eval.py`. Do not put a judge await on `/ai/chat` or `/ai/agent`
- [ ] 3.4 Add CI-safe unit tests under `tests/evals/` for fail-closed helpers / SKIP classification only (no live HTTP, no judge network, no DeepEval paid calls in pytest)

## 4. Apply validation (must prove it works)

- [ ] 4.1 Run L0 from repo root: `$env:PYTHONPATH = "src"; python evals/run_eval.py --mode fixture` — confirm still green (or record honest fixture `PASS: X/Y`)
- [ ] 4.2 Bring up local Compose (or reachable staging); verify `GET /health` and `GET /health/ai`; obtain JWT. Prefer a quick L1 smoke on the same stack when practical
- [ ] 4.3 `pip install -r evals/requirements-quality.txt`; set `GEMINI_API_KEY_2`; seed answer notes if needed; run `python evals/run_quality.py --token "<jwt>" --base-url http://127.0.0.1` (optional `--limit` for first pass). If product Gemini **429** / quota blocks chat or embed, switch to a different NVIDIA NIM free/catalog model via `LLM_MODEL` / `LLM_MODEL_FALLBACKS`, recreate `api` + `worker`, and re-run — do not invent scores. If judge 429/503, re-run or adjust `--judge-model`; never use product `GEMINI_API_KEY`
- [ ] 4.4 Record the actual L2 aggregates, judge model, `n`, SKIP count/reasons, environment `lab` or `pre-deploy`, and date in `evals/README.md`. Apply is incomplete if zero cases were scored without an honest fail-closed explanation. Optionally add a dated EXPERIMENTS row. Do not reuse a RAGAS row as L2 proof
- [ ] 4.5 Confirm `.github/workflows/ci.yml` still runs fixture-only (no quality CLI, no judge key, no L2 merge gate)
