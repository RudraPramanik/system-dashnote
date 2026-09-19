## Why

A full 12-case L2 live run (`evals/run_quality.py --seed-live`) seeds notes, then crashes on the first `POST /ai/chat` with uncaught `httpx.ReadTimeout` (client timeout 180s). Collection already SKIPs HTTP errors and empty answers, but a transport timeout aborts the whole suite, so operators never get SKIP counts, remaining cases, or a fail-closed `n=0` summary. NVIDIA NIM Lightning RAG chat can exceed 180s on a cold first turn; the runner must survive that.

## What Changes

- Treat live collection **timeouts and other HTTP transport failures** on `POST /ai/chat` (and the follow-up `/ai/test-search` if it times out after a successful chat) as **SKIP with a reason**, not an uncaught traceback. Existing fail-closed `n=0` behavior stays.
- Give collection a **longer default HTTP timeout** (and optionally one retry on timeout) so a slow first NIM chat is less likely to die at 180s, without putting a judge on `/ai/chat`.
- CI-safe tests that a timeout is classified as SKIP and that `_collect_row` does not raise when the client times out (mocked HTTP, no live stack).
- Operator docs: PowerShell must not paste `>>` comment lines from docs; do not paste JWTs into chat or artifacts; `--limit` remains the smoke path; full-set timeouts SKIP then fail-closed if nothing scores.
- Do **not** add DeepEval to the API image or PR CI. Do **not** change product chat latency or put a judge on the hot path. Do **not** copy live JWT tokens into this change.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-eval-harness`: L2 collection SKIPs transport timeouts (and similar request errors) instead of crashing; timeout/retry policy is part of the live collection contract; apply MUST prove a full-set run no longer dies with `httpx.ReadTimeout`.
- `eval-lifecycle`: Blueprint / README honesty fields MUST list collection timeout as a SKIP reason (alongside non-200, empty answer, empty retrieval), not as an unhandled crash.

## Impact

- **Eval:** `evals/run_quality.py` `_collect_row` / live client timeout; `evals/quality_lab.py` skip classifier; `tests/evals/test_quality_lab.py`; `evals/README.md` and `evals/BLUEPRINT.md` operator notes.
- **Product API / worker / Compose / CI:** unchanged. PR CI stays L0 fixture-only. No new runtime deps.
- **Secrets:** artifacts MUST NOT contain JWTs. Operators rotate any token that was pasted into a terminal or chat.
- **Non-goals:** No product LLM timeout / `AGENT_TOOL_TIMEOUT` rewrite unless collection still cannot complete after the harness fix; no agent answer goldens; no treating SKIPs as scored success; no DeepEval on the API image.
- **Apply gate:** Implementation is not complete until a live `run_quality.py --seed-live` against the lab stack either finishes all cases (with timeouts recorded as SKIP) or fail-closes on `n=0` **without** an uncaught `httpx.ReadTimeout` traceback. Record the actual `n` / SKIP reasons. Do not reuse the `--limit 2` 2026-09-19 row as proof this crash is gone.
