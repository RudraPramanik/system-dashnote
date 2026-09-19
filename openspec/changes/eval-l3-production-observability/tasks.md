## 1. Docs and layer alignment

- [x] 1.1 Update `evals/BLUEPRINT.md`: mark L0/L1/L2 done; mark **L3 production observability** as this phase; keep thresholds / generator / agent answers / nightly judge CI as later phases; keep L0/L1 shared goldens + scorers (fixtures = recorded contract); add L2/L3 placement (JWT `wid` traces/feedback; L3 does not replace `PASS: X/Y` or GEval; never await a judge on `/ai/chat` or `/ai/agent`)
- [x] 1.2 Update `evals/README.md`: L3 procedure (Langfuse UI parent `rag.answer` / `agent.turn`, `POST /ai/feedback`, `GET /metrics` quality counters); env var names `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, alias `LANGFUSE_BASE_URL`; L0/L1 alignment note; L2 stays pre-deploy; PR CI stays fixture-only; placeholders only — no live keys or JWTs
- [x] 1.3 Update `docs/documentation/observe.md` (and `.env.example` if needed) so `LANGFUSE_HOST` remains canonical and `LANGFUSE_BASE_URL` is documented as an alias. Do not add Langfuse keys to CI or as a hard `/health` gate

## 2. Production-shaped Langfuse env

- [x] 2.1 Add `LANGFUSE_BASE_URL` on Settings and `effective_langfuse_host` (prefer non-blank `LANGFUSE_HOST`, else `LANGFUSE_BASE_URL`, else cloud default). Point `get_langfuse_client()` at that host. `langfuse_enabled` stays both keys non-empty
- [x] 2.2 Add CI-safe unit tests for the host alias and disabled-when-keys-missing behavior (no live Langfuse network in pytest)
- [x] 2.3 Do not import the Langfuse SDK from `src/ai/*`. Do not put GEval/RAGAS on the chat or agent request path

## 3. Feedback and serving confirmation

- [x] 3.1 Confirm `POST /ai/feedback` still authorizes by JWT `wid`, accepts thumbs or 1–5, returns 2xx `tracing=unavailable` when Langfuse is off, and rejects foreign-workspace threads. Extend tests only if a gap is found — do not change the request body
- [x] 3.2 Confirm existing observability tests still pass (`tests/observability/`, `tests/ai_routes/test_feedback.py`) and `/metrics` still exposes `dashnote_ai_empty_retrieval_total`, `dashnote_ai_agent_interrupt_total`, `dashnote_ai_llm_fallback_total` without per-user judge labels
- [x] 3.3 Do not add L3 cases to `evals/run_eval.py` or treat traces/thumbs as a merge gate

## 4. Apply validation (must prove it works and stays aligned)

- [x] 4.1 Run L0 alignment check from repo root: `$env:PYTHONPATH = "src"; python evals/run_eval.py --mode fixture` — confirm still green (or record honest fixture `PASS: X/Y`). Do not claim L0/L1 alignment from an older row only
- [x] 4.2 Bring up local Compose (or reachable staging) with Langfuse keys loaded into the API process (operator `.env` / `.env.production` — do not paste secrets). Verify `GET /health` and `GET /health/ai`. Recreate `api` after env changes. If Gemini **429** blocks chat/embed, use the NVIDIA NIM hatch and recreate `api` + `worker`
- [x] 4.3 When a JWT is available, run L1 on the same stack (`python evals/run_eval.py --mode live --base-url … --token … --seed-live`) and record honest `PASS: X/Y` + SKIPs, or name why live was blocked. Confirm docs still state one golden corpus / one scorer
- [x] 4.4 Prove L3: `POST /ai/chat` (or agent) → `thread_id`; confirm a `rag.answer` or `agent.turn` parent in Langfuse UI; `POST /ai/feedback` → 2xx; `GET /metrics` still has `dashnote_ai_*` counters. If traces are missing, record the honest cause (host alias, init, outbound) — do not invent a successful row
- [x] 4.5 Record dated L0 (and L1 if run) plus L3 proof in `evals/README.md`. Optionally add a short EXPERIMENTS note. Confirm `.github/workflows/ci.yml` still runs fixture-only (no Langfuse, no feedback, no L2/L3 merge gate)
