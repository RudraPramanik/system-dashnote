## Context

See `proposal.md` for motivation. Today:

- L0 is closed: fixture mode, scoring tests, keyless CI, product LLM walk on 429 → next `LLM_MODEL_FALLBACKS` (extra NIM before Gemini Flash).
- L1 already exists as `evals/run_eval.py --mode live` (HTTP `GET /ai/test-search`, optional `--seed-live`, dual tokens). Last README live row is **2026-09-06 PASS: 8/8 (7 skipped)** — not proof of this change.
- Live skips: `mode_hint=fixture` cases, trajectories (“not wired”), tenant `actor=b` without `--token-b`.
- Shared scoring (`score_case` / `normalize_search_payload`) is already the L0/L1 bridge; docs and roadmap still treat L1 as “exists” without an apply gate or explicit L0 alignment language.
- Gemini 429 on live collection remains an operator concern; product hatch is shipped — L1 must **use and document** it, not reimplement fallback unless apply finds a gap.

## Goals / Non-Goals

**Goals:**

- Close L1 as the second post-blueprint implementation: live contract for eligible retrieval/tenant goldens, L0/L1 alignment in docs + behavior, honest live `PASS: X/Y` from a run during apply
- Operator procedure for NIM (different free model) when Gemini 429 blocks the live stack
- Keep PR CI fixture-only; keep SKIP vs FAIL honest

**Non-Goals:**

- `run_quality.py`, `rag_answers.jsonl`, DeepEval
- Making L1 a PR merge gate or requiring live tokens in CI
- Full live agent trajectory suite (fixture-primary stays unless a tiny safe path is already free)
- Changing product tenancy or search surfaces
- Default Super 120B / Ultra 550B hops

## Decisions

### 1. One runner, two modes — do not fork L1

**Choice:** Keep `evals/run_eval.py` as the C-gate + live contract. Harden live path and docs; do not add `run_live.py`.

**Why:** Blueprint already names one CLI for L0/L1. A second entrypoint drifts scoring.

**Alternative:** Separate live package — rejected.

### 2. L0/L1 alignment = shared goldens + shared scorers + mode hints

**Choice:** Alignment means (a) same JSONL case ids and marker expectations, (b) same `score_case` / payload normalize for search themes, (c) `mode_hint` / `skip_if_modes` as eligibility law, (d) README/BLUEPRINT stating fixtures are the recorded L1 contract. Do **not** require every fixture-only case to become live in this change (e.g. empty-hit shape cases, duplicate marker fixtures can stay `fixture`).

**Why:** Live empty-retrieval and some isolation cases need environment control that CI fixtures already prove; forcing them live adds flake without hiring value.

**Alternative:** Promote all 20 cases to live — rejected for this phase; record honest SKIPs instead.

**Apply check:** After runner/docs work, run fixture mode once to confirm L0 still **PASS: 20/20** (or honest current), then run live and record.

### 3. Live surface stays `GET /ai/test-search` (+ seed notes)

**Choice:** L1 contract remains retrieval/tenant via test-search and note seeding. Do not expand L1 into `POST /ai/chat` answer goldens (that is L2 collection).

**Why:** Keeps L1 as PASS/FAIL contract, not GEval. Chat collection belongs to `run_quality.py` later.

**Alternative:** Live chat smoke in L1 — rejected; blurs layers.

### 4. NIM hatch is operator + product config, not eval runner logic

**Choice:** When live fails because the stack’s Gemini candidate is 429, operators set/adjust `LLM_MODEL` / `LLM_MODEL_FALLBACKS` to a different entitled NVIDIA NIM free/catalog id (already documented defaults include `nvidia_nim/openai/gpt-oss-20b` before Gemini Flash), recreate `api` + `worker`, and re-run L1. The eval CLI does **not** embed provider keys or switch models itself.

**Why:** Fallback already lives in `shared/llm/fallback.py`. Duplicating it in `run_eval.py` would mix product and harness concerns.

**Alternative:** Eval CLI passes a model override header — rejected; no such product API.

**If apply hits 429:** Document the hatch used and the successful re-run; do not invent PASS.

### 5. Apply is not done until live eval is validated

**Choice:** Final implementation tasks MUST:

1. Confirm L0 still green: `python evals/run_eval.py --mode fixture`
2. Bring up Compose (or use a reachable staging URL), obtain JWT(s), optionally `--seed-live`
3. Run `python evals/run_eval.py --mode live --base-url … --token …` (+ `--token-b` when validating member deny)
4. On Gemini 429 / chat-fallback or embed failures tied to quota, switch to a different NIM free model, recreate services, re-run
5. Record actual `PASS: X/Y`, SKIP count/reasons, environment `live-local`, date in `evals/README.md`

Exit non-zero on scored failures. A run with **zero scored cases** (all SKIP) fails the apply gate.

**Alternative:** Docs-only L1 — rejected; user required validation.

### 6. Blueprint roadmap renumber

**Choice:** Update `evals/BLUEPRINT.md` phased table so after done L0, the next phase is **L1 live contract**, then former “phase 2” DeepEval becomes the following phase. Keep “each phase is a separate OpenSpec change.”

**Why:** Current table jumps L0 → DeepEval and marks L0 as “this change” (stale). User asked for L1 as step 2.

## Risks / Trade-offs

- **[Risk] Live flake from embed latency / cold Qdrant** → Mitigation: `--seed-live` with documented `wait_embed_sec`; single shared wait; retry once after extra wait before FAIL; honest SKIP only when mode_hint says so.
- **[Risk] Gemini 429 still blocks despite NIM defaults** → Mitigation: ping entitled NIM ids; swap `LLM_MODEL` / fallbacks; recreate api+worker; clear stuck in-process cache by recreate; never fabricate scores.
- **[Risk] Dual-token setup friction** → Mitigation: document membership prep; SKIP with explicit reason when `--token-b` missing; fixture mode remains isolation proof for CI.
- **[Risk] Scope creep into L2** → Mitigation: no answer goldens, no DeepEval import from `run_eval.py`.
- **[Trade-off] Not all goldens run live** → Accepted; L0 covers fixture-only cases; L1 proves the `either`/`live` set against a real API.

## Migration Plan

1. Docs + roadmap + any small runner SKIP/message hardening
2. Optional CI-safe unit tests only if live eligibility/SKIP helpers need coverage (no live HTTP in pytest)
3. Operator validation: fixture then live; NIM hatch if needed
4. Record README rows; leave CI workflow fixture-only
5. Rollback: revert docs/runner tweaks; product NIM fallbacks already shipped stay unless this change altered them

## Open Questions

- None that block planning. Which exact NIM free id to use if `gpt-oss-20b` is untitled for the operator is answered during apply by pinging entitled catalog models (same practice as L0) — not a spec change.
