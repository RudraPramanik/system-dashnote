## 1. Collection timeout SKIP

- [x] 1.1 Add a helper (e.g. `transport_skip_reason`) in `evals/quality_lab.py` that maps HTTP client timeout / other request-transport failures to a stable SKIP reason (`chat timeout`, `search timeout`, or transport error). Update `COLLECTION_FAILURE_HINT` to mention timeout / slow NIM chat, not only HTTP 500 / 429
- [x] 1.2 In `evals/run_quality.py`, default collection HTTP timeout to ≥300s; add optional `--timeout` seconds. Catch timeout and other request-transport errors inside `_collect_row` for `POST /ai/chat` and `GET /ai/test-search`; return SKIP instead of raising
- [x] 1.3 Retry `POST /ai/chat` once after a timeout (short backoff). Do not retry HTTP 4xx/5xx or empty-body SKIPs. Remaining goldens MUST still run after a SKIP
- [x] 1.4 Do not change product `/ai/chat` latency, LiteLLM fallbacks, `AGENT_TOOL_TIMEOUT`, API/worker images, or PR CI

## 2. Tests and docs

- [x] 2.1 Extend `tests/evals/test_quality_lab.py` (and a mocked `_collect_row` test) so `httpx.ReadTimeout` / connect errors become SKIP reasons and `_collect_row` does not raise. No live HTTP, no DeepEval network
- [x] 2.2 Update `evals/BLUEPRINT.md` and `evals/README.md`: timeout / transport failure is SKIP; full-set all-SKIP is fail-closed; `--limit` is the smoke path; PowerShell command examples MUST NOT include `>>` comment lines; NEVER paste or document a live JWT

## 3. Apply validation (must prove the crash is gone)

- [x] 3.1 Run `python -m pytest tests/evals/test_quality_lab.py -q` from repo root
- [x] 3.2 Re-run live L2 against the lab stack: `python evals/run_quality.py --token <jwt> --base-url http://127.0.0.1 --seed-live --environment lab` (one PowerShell command, no `>>`). The process MUST NOT die with uncaught `httpx.ReadTimeout`. Timeouts MAY SKIP; later cases MUST still be attempted
- [x] 3.3 Record the actual `n`, SKIP count/reasons, aggregates (or honest fail-closed `n=0`), judge model, environment `lab`, and date in `evals/README.md`. Do not reuse the 2026-09-19 `--limit 2` row as proof this crash is gone. Do not write JWTs into the README
