## Why

L0 fixture-gate close-out is done (keyless CI, scoring tests, NIM 429 hatch on the product LLM walk). The next eval layer is **L1 live API contract**: the same goldens against a real Compose/staging stack. Today `run_eval.py --mode live` exists but the last recorded run was **PASS: 8/8 with 7 skipped**, live trajectories are explicitly unwired, L0/L1 sharing of scoring and case eligibility is not spelled as a contract, and Gemini free-tier **429** still blocks live collection unless operators pin NVIDIA NIM (different free/catalog model) via the product candidate list. Without a closed L1 apply, later L2 quality work would collect answers against an unproven live contract.

## What Changes

- Close **L1 as the second eval implementation phase** after L0: operator/nightly live contract against local Compose (or staging), same retrieval/tenant goldens and shared scoring as fixture mode, honest recorded `PASS: X/Y` with SKIP reasons.
- **Align L0 with L1**: shared scorer and payload normalization; `mode_hint` / `skip_if_modes` remain the eligibility law; fixture cases that are `either` MUST score identically when the live stack returns the same hit shape; README/BLUEPRINT MUST state that L0 fixtures are the recorded form of the L1 contract, not a separate corpus.
- Operator path when Gemini is rate-limited: use NVIDIA NIM with a **different free/catalog model** (`LLM_MODEL` / `LLM_MODEL_FALLBACKS`, recreate `api` + `worker`) so live search/seed/embed can proceed. L1 itself does not call a judge and does not put GEval on `/ai/chat` or `/ai/agent`.
- Harden live runner ergonomics: clear SKIP vs FAIL, dual-token tenant path, `--seed-live` documented and reliable, environment label `live-local` (or staging) on the recorded row.
- **Mandatory apply validation**: run live eval against a reachable stack and record the actual summary. Do not claim L1 works from the 2026-09-06 row.
- Do **not** implement L2 (`run_quality.py`, DeepEval, answer goldens). Do **not** make L1 a PR merge gate (CI stays L0 fixture-only). Live agent trajectory scoring remains optional / fixture-primary unless a small safe live path is already feasible without expanding into L2.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-eval-harness`: L1 live mode is a first-class contract — same goldens/scoring as L0 for eligible cases, operator docs for `--mode live` + NIM 429 hatch, apply MUST prove a live run with recorded `PASS: X/Y` and SKIP honesty.
- `eval-lifecycle`: Second follow-on after L0 is L1 live contract (not L2). Blueprint roadmap/README MUST place L1 between L0 and the planned DeepEval quality suite; NIM remains the Gemini quota hatch for live layers; PR CI stays fixture-only.

## Impact

- **Eval:** `evals/run_eval.py` live path, `evals/README.md`, `evals/BLUEPRINT.md` phased roadmap (insert L1 after L0). Shared scoring stays the L0/L1 bridge; goldens under `evals/golden/` may get `mode_hint` / seed / docs tweaks only where needed for live eligibility — no answer-golden files.
- **LLM / product:** No new judge keys. Live stack continues to use existing `LLM_MODEL` / `LLM_MODEL_FALLBACKS` (NIM before Gemini Flash). Operators recreate `api` + `worker` after fallback changes. Product 429 walk is already shipped; this change consumes it for L1 docs + validation, not a second fallback implementation unless a live gap is found during apply.
- **CI:** Unchanged — fixture-only in `.github/workflows/ci.yml`. L1 remains operator / nightly.
- **Tenancy:** Unchanged. JWT `wid` only; `--token-b` for member deny cases; forged workspace probe still ignored.
- **Non-goals:** No DeepEval, no `run_quality.py`, no collapsing chat/agent, no judge on the hot path, no L1 as PR merge gate, no treating live PASS rates as production SLOs.
- **Apply gate:** Implementation is not complete until live eval is run against a real base URL with a JWT and the actual `PASS: X/Y` (plus SKIP count/reasons) is recorded in `evals/README.md`. If Gemini 429 blocks the stack, apply MUST switch to a different NIM free model and re-validate — not invent scores.
