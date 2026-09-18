## Context

See `proposal.md` for motivation. Today:

- L0 already has `evals/run_eval.py --mode fixture`, goldens, fixtures, and a CI step. There are **no** pytest tests for scoring (`tests/evals/` only covers RAGAS helpers).
- `evals/README.md` layout is stale vs `evals/BLUEPRINT.md`. Latest recorded fixture row is historical, not proof of this change.
- Product LLM walk in `src/shared/llm/fallback.py` continues on HTTP 410 / model-gone and wall-clock timeout only. `acompletion_with_retry` retries `RateLimitError` on the **same** candidate, then re-raises; fallback does not walk. Cached success can stick on an exhausted Gemini id (seen in the RAGAS lab: chat HTTP 500 / 429).
- Default `LLM_MODEL_FALLBACKS` is only `gemini/gemini-2.5-flash`. Primary is already NVIDIA NIM Lightning.

L0 fixture itself never calls an LLM. The 429 walk is for later live layers and product chat so Gemini quota cannot pin the process.

## Goals / Non-Goals

**Goals:**

- Close L0 as the first post-blueprint implementation: CI-safe scoring tests, operator docs, honest fixture `PASS: X/Y` from a run during apply
- Walk LLM candidates on exhausted rate-limit / 429; keep the rate-limited id out of the process cache
- Put a second live NVIDIA NIM free/catalog id in documented fallbacks **before** Gemini Flash
- Keep PR CI fixture-only and keyless

**Non-Goals:**

- `run_quality.py`, `rag_answers.jsonl`, DeepEval, L1 live as a merge gate
- Changing retry counts / backoff on a single candidate
- Scraping NVIDIA `/v1/models` as the only resolver
- Default hops to Super 120B / Ultra 550B
- Collapsing `/ai/chat*` and `/ai/agent*`

## Decisions

### 1. Do not rewrite the L0 runner

**Choice:** Keep `evals/run_eval.py` as the C-gate. Add tests that import its scoring helpers the same way `tests/evals/test_ragas_lab.py` imports `ragas_lab` (put `evals/` on `sys.path`). Cover `score_case` / `score_trajectory` with in-memory payloads (marker miss, tenant leak, forbidden `create_note`). Optionally assert fixture mode needs `fixture_ref` and that `chat_payload`-style live helpers are out of scope.

**Why:** The runner already prints `PASS: X/Y` and is wired in `.github/workflows/ci.yml`. A rewrite risks the hire C-gate.

**Alternative:** New `evals/l0.py` package — rejected; extra surface for no behavior gain.

**Apply:** New `tests/evals/test_run_eval.py` (name may vary). Pytest CI picks it up; do not add a second CI eval job.

### 2. Apply is not done until fixture evals are run

**Choice:** Last implementation task MUST run, from repo root:

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture
```

Record the actual `PASS: X/Y` in `evals/README.md` with today’s date. Exit non-zero fails apply. Do not copy the 2026-09-07 row.

**Why:** Specs require an honest recorded rate. User asked to validate L0 after implementation.

**Alternative:** Trust CI only — rejected; apply must prove locally.

### 3. Docs: L0 keyless + NIM quota hatch; L2 still later

**Choice:** Update `evals/README.md` layout (include `BLUEPRINT.md`, `agent_trajectory.jsonl`) and a short quota note: fixture needs no Gemini/NIM keys; if live chat collection later hits Gemini 429, use NVIDIA NIM with a different free model via `LLM_MODEL` / `LLM_MODEL_FALLBACKS` and recreate `api` + `worker`. Patch `evals/BLUEPRINT.md` phased roadmap so phase 1 is this L0 close-out and DeepEval stays a later phase; add a Judge/quota line that NIM is the 429 hatch for live layers, not a hot-path judge.

**Why:** Matches `eval-lifecycle` delta without shipping L2.

**Alternative:** Docs-only quota note without fallback code — rejected; the 429 stickiness is a product bug that already broke live eval collection.

### 4. Rate-limit walk after per-candidate retry exhaustion

**Choice:** Extend `shared/llm/fallback.py`:

- Add `is_rate_limited(exc)` (HTTP 429, `litellm.exceptions.RateLimitError`, quota/rate-limit text) analogous to `is_model_gone`.
- On that error (after `_invoke_candidate` returns — i.e. after tenacity retries on non-stream), increment fallback metric, log, `_mark_gone` (reuse skip set so the id is not cached as success), continue to the next candidate.
- Do **not** treat 429 as 410 in log wording.
- Auth / bad-request still fail closed (no walk).
- Chat and agent already share `acompletion_with_fallback`; no route merge.

**Why:** Per-model retries still absorb burst 429s. Walking after exhaustion is what unsticks Gemini quota. Skip-set reuse matches the RAGAS lab failure (cached exhausted model).

**Alternative:** Disable RateLimitError in tenacity and walk immediately — rejected; would thrash fallbacks on brief 429s.

**Alternative:** Clear cache but retry the same Gemini id next request — rejected; that is the sticky-quota bug.

**Apply:** Unit tests in `tests/shared/test_llm_fallback.py` (no live HTTP): 429 on first candidate, success on later NIM id; subsequent call does not start on the 429 id; all-429 raises `LLMUnavailableError`.

### 5. Second NIM id in documented fallbacks

**Choice:** Default shape:

```text
LLM_MODEL=<current live small NIM, Lightning class>
LLM_MODEL_FALLBACKS=<different live small NIM>,gemini/gemini-2.5-flash
```

During apply, ping 1–3 small NVIDIA NIM ids that are **not** the primary and **not** Super 120B / Ultra 550B using `scripts/test_nvidia_nim.py` (or equivalent). First entitled (not 410/404) becomes the extra fallback. If none entitled, keep Lightning primary, leave Gemini as last hop, and document the operator-chosen NIM id in comments — do not invent a dead catalog id as if it were verified.

**Why:** Hosted NIM ids EOL often. Catalog listing ≠ entitled. User asked for a different free NIM when Gemini is rate-limited; the extra NIM hop must sit **before** Gemini so 429 on Gemini can land on NIM, and 429 on primary NIM can land on the other NIM instead of Gemini.

**Alternative:** Gemini-only fallbacks — rejected; that is today’s failure mode.

**Apply:** Update `.env.example`, `src/config.py` default `LLM_MODEL_FALLBACKS` if it should match example, `docs/documentation/ai.md`. Local `.env` is operator-owned; recreate `api` + `worker` after change. Do not commit live keys.

### 6. L0 validation vs live L1

**Choice:** Required proof is fixture mode only. Optional live `--mode live` is **not** a blocking apply task (needs JWT, Compose, embeds). If the operator already has a stack up, a live smoke may be noted in EXPERIMENTS, but L0 close-out does not depend on it.

**Why:** L0 is defined as deterministic CI. Live is L1.

## Risks / Trade-offs

- **[Risk] Second NIM id is 410 by the time apply runs** → Mitigation: ping during apply; rotate; never pin nano/glm-5.2/120B as the new default hop.
- **[Risk] Walking on 429 hides a real billing/quota problem** → Mitigation: log each hop; skip the limited id for the process; `/health` stays up; fail closed if every candidate 429s.
- **[Risk] Tenacity retries + fallback walk multiply latency** → Mitigation: keep existing `LLM_MAX_RETRIES` and wall clock; do not add extra sleep in fallback.
- **[Risk] L0 “implementation” looks like a no-op because the runner exists** → Mitigation: tests + fresh PASS row + quota hatch are the deliverable; do not rewrite goldens.
- **[Trade-off] Reusing `_skip` for 429 and 410** → Quota recovers after restart (same as today’s gone-cache). Accept process-lifetime skip rather than a TTL in this change.
- **[Trade-off] Product LLM change inside an eval L0 change** → Needed so later live evals are not blocked; fixture CI stays keyless.

## Migration Plan

1. Add pytest scoring coverage; keep CI fixture step as-is.
2. Implement 429 walk + tests; update example fallbacks after NIM ping.
3. Patch README + BLUEPRINT (L0 first; NIM hatch; phase list).
4. Run fixture evals; write the actual `PASS: X/Y` into README.
5. Recreate local `api` + `worker` only if `.env` fallbacks changed.
6. Rollback: revert fallback.py / env example; L0 tests and docs can stay independently.

## Open Questions

None that block planning. The exact second NIM catalog id is chosen during apply by ping, not frozen in this design.
