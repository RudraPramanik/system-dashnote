## Context

See `proposal.md` for why. L2 already SKIPs non-200 / empty answer / empty retrieval in `classify_collection_skip`, then fail-closes on `n=0`. `_collect_row` calls `POST /ai/chat` then `GET /ai/test-search` with `httpx.Client(..., timeout=180.0)` and does not catch transport errors, so `httpx.ReadTimeout` kills the suite before later cases or the fail-closed summary. Product chat on NVIDIA NIM Lightning can exceed 180s on a cold first turn after `--seed-live`. Specs: `specs/ai-eval-harness/spec.md`, `specs/eval-lifecycle/spec.md`.

## Goals / Non-Goals

**Goals:**
- Collection timeouts and other HTTP transport failures become SKIP reasons; remaining cases still run.
- Default collection timeout is at least 300s; one retry on chat timeout.
- CI-safe tests cover classifier + mocked `_collect_row` (no live HTTP, no DeepEval network).
- Docs list timeout as SKIP, warn against PowerShell `>>` paste and embedding JWTs.

**Non-Goals:**
- Changing product `/ai/chat` latency, LiteLLM fallbacks, or `AGENT_TOOL_TIMEOUT`.
- Adding DeepEval to the API image or PR CI.
- Treating timeout SKIPs as scored success.
- Rewriting goldens or judge metrics.

## Decisions

1. **Catch transport errors inside `_collect_row`, not only the live loop.** Catch `httpx.TimeoutException` and other `httpx.RequestError` on chat and on test-search. Return `(None, reason)` so `_run_live`’s existing SKIP path prints the case id and continues. Do not catch `HTTPStatusError` here — non-200 already goes through `classify_collection_skip`.

   *Alternative:* wrap the whole `for case` loop. Rejected: one timeout would still be easy to mishandle, and search vs chat reasons would blur.

2. **Default HTTP timeout 300s; optional `--timeout` seconds.** 180s is what the 12-case lab hit. Isolated judge calls already ran ~184s; product RAG on NIM can be slower than that. 300s is the spec floor. CLI override lets operators raise further without a code change.

   *Alternative:* 600s with no retry. Rejected: a hung API would stall every case for 10 minutes. Timeout + one retry is enough for a cold first token.

3. **Retry chat once on timeout only.** After a chat `TimeoutException`, wait a short backoff (a few seconds) and POST once more. If the retry times out or any `RequestError` occurs, SKIP. Do not retry HTTP 4xx/5xx or empty-body SKIPs.

   *Alternative:* no retry, only raise timeout. Possible but a single cold NIM turn would SKIP the first golden every full run.

4. **Search timeout after a successful chat is SKIP (`search timeout`), not a silent empty-retrieval skip.** If chat returned an answer but test-search never completes, do not judge with missing context.

5. **Keep fail-closed `n=0`.** All-timeout runs print SKIP reasons + `COLLECTION_FAILURE_HINT` and exit 1. Hint text MUST mention timeout / NIM slowness, not only HTTP 500 / 429.

6. **Tests:** extend `classify_collection_skip` or add a small `transport_skip_reason(exc)` helper used by `_collect_row`. Pytest uses a stub client that raises `httpx.ReadTimeout` / `httpx.ConnectError`. Import `run_quality._collect_row` in `tests/evals/` with the same evals-on-`sys.path` pattern as `quality_lab` (no live base URL).

7. **Docs only for the PowerShell `>>` failure.** That traceback is copy-paste of a markdown comment, not a Python bug. README command blocks MUST be paste-safe (no `>>` prefixes). Never write live JWTs into artifacts or README.

## Risks / Trade-offs

- **[Risk]** 300s × 12 cases × retry can make a hung stack run for hours → Mitigation: `--limit` for smoke; `--timeout` documented; fail-closed still ends the run after collection; do not retry non-timeout errors.
- **[Risk]** SKIP-all timeouts look like “the suite ran” → Mitigation: `n=0` still exits non-zero; apply MUST NOT record that as a successful L2 close-out.
- **[Risk]** Raising timeout hides a stuck API → Mitigation: SKIP reason names timeout; operators still inspect API logs / NIM health.
- **[Risk]** Pasted JWTs in terminals/chat → Mitigation: artifacts contain none; README tells operators to mint a fresh token and rotate leaked ones.

## Migration Plan

- Laptop-only eval harness. No Compose/API/worker deploy. No rollback of product images.
- After apply, operators re-run `python evals/run_quality.py --token <jwt> --base-url http://127.0.0.1 --seed-live --environment lab` (PowerShell: one command, no `>>` lines). Record actual `n` / SKIP reasons. If every case still times out, that is an honest fail-closed product/NIM issue, not a harness crash.

## Open Questions

None. Product `AGENT_TOOL_TIMEOUT` stays out of scope unless a post-fix live run shows chat never returning even after 300s + retry; that would be a follow-on change.
