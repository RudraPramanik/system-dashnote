## 1. Operator extra and env placeholder

- [ ] 1.1 Add `evals/requirements-ragas.txt` with a pinned `ragas` range and Gemini-capable extras; do **not** add ragas to API `requirements.txt` or Compose images
- [ ] 1.2 Add empty `GEMINI_API_KEY_2=` to `.env.example` with comments: local RAGAS/judge only, not embeddings, not VPS; leave `.env.production.example`, Compose, and `src/config.py` unchanged

## 2. RAGAS lab CLI

- [ ] 2.1 Isolate judge-key loading (strip whitespace; require `GEMINI_API_KEY_2`; never fall back to `GEMINI_API_KEY` or set that env var)
- [ ] 2.2 Add `evals/run_ragas.py` `--setup` that prints install, env, and run commands with no network/judge calls
- [ ] 2.3 Implement `--live` (default base URL `http://127.0.0.1`, `--token`, `--limit` default 5): `POST /ai/chat` with `{ "message" }` only; map answer + citation texts; skip `ret-08` and zero-context cases; skip tenant/trajectory goldens
- [ ] 2.4 Wire RAGAS faithfulness + context precision with Gemini Flash via `llm_factory` / `--judge-model`; print aggregate scores; exit non-zero if the judge key is missing

## 3. Tests (CI-safe)

- [ ] 3.1 Unit-test fail-closed credential check (`GEMINI_API_KEY` set, `GEMINI_API_KEY_2` empty → refuse) without importing ragas (`tests/evals/` or equivalent)
- [ ] 3.2 Extend `tests/observability/test_compat_gate.py` (or sibling) so CI workflow does not invoke `run_ragas.py` / ragas
- [ ] 3.3 Confirm live collection helper never sends `workspace_id` in the chat body

## 4. Docs and operator record

- [ ] 4.1 Document setup + `--setup` / `--live` in `evals/README.md`; state not CI, not VPS; keep Langfuse faithfulness section; link EXPERIMENTS
- [ ] 4.2 Update `docs/documentation/observe.md` and `docs/documentation/blueprint8.md` so RAGAS is a runnable local/nightly lab (laptop), not a VPS or PR gate
- [ ] 4.3 Add EXP-00N in `docs/EXPERIMENTS.md` labeled `lab` or `live-local`, not a production SLO; fill After from a `--live` run when Compose is up, otherwise record the command honestly as pending

## 5. Compatibility gate

- [ ] 5.1 `python evals/run_eval.py --mode fixture` still prints `PASS: 20/20` (or current honest X/Y)
- [ ] 5.2 `python evals/run_ragas.py --setup` prints the operator checklist
- [ ] 5.3 Confirm API Settings / Compose / production env example still have no `GEMINI_API_KEY_2`; chat/agent HTTP contracts unchanged
