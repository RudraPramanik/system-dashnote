## Context

See `proposal.md` for why. Archive `nightly-ragas-lab` already shipped `evals/run_ragas.py` assuming RAGAS docs’ `llm_factory(model, provider="google", client=...)`. Operator install resolved `ragas==0.3.2` because `evals/requirements-ragas.txt` capped `datasets<4`, while newer 0.3.x needs `datasets>=4`. In 0.3.2, `llm_factory` is OpenAI-shaped only (`model`, `run_config`, …) — no `provider`/`client` — so `--live` dies after COLLECT. Current RAGAS main (0.4.x) matches the Google factory the script already calls. Credential law unchanged: `GEMINI_API_KEY_2` only; never assign product `GEMINI_API_KEY`.

## Goals / Non-Goals

**Goals:**

- Make documented `pip install -r evals/requirements-ragas.txt` + `--live` print faithfulness + context precision on ≥1 collected row.
- Keep CI free of ragas imports; keep API image / Compose / VPS untouched.
- Clear operator error if the installed stack still cannot build a Gemini judge.

**Non-Goals:**

- Fixing product `POST /ai/chat` 500 on `ret-05` (SKIP remains valid).
- Switching default judge to OpenAI / OpenRouter.
- Raising `--limit`, adding metrics, or promoting scores to SLOs.
- Importing ragas into pytest CI.

## Decisions

### 1. Prefer bumping the operator pin to Gemini-capable RAGAS (0.4.x lane)

Update `evals/requirements-ragas.txt` to allow a RAGAS release whose `llm_factory` accepts `provider="google"` + `client=` (today: `ragas>=0.4,<0.5` or the narrowest verified range at apply time). Relax `datasets<4` to whatever that RAGAS release requires (e.g. `datasets>=2.14` without an artificial `<4` ceiling, or match upstream).

**Why:** The script and archived design already target the Google factory; aligning the pin removes the mismatch instead of rewriting judge wiring twice.

**Alternative considered:** Stay on `ragas<0.4` and wrap `LangchainLLMWrapper(ChatGoogleGenerativeAI(...))`. Viable fallback if 0.4 breaks evaluate/metrics APIs used by the lab — use only if apply-time install of 0.4 fails or metrics constructors diverge badly.

**Alternative considered:** Dual-path try/except on `provider=`. Rejected as primary — hides pin bugs; prefer one documented path + fail with a pin hint.

### 2. Keep evaluate call shape; isolate judge build in one helper

Keep metrics: Faithfulness + ContextPrecision. Extract a small `build_gemini_judge_llm(judge_key, judge_model)` (in `ragas_lab.py` only if it stays import-safe without ragas at module import — otherwise keep inside `run_ragas.py` behind the existing import gate). Still set in-process `GOOGLE_API_KEY` from the judge key only; never copy into `GEMINI_API_KEY`.

**Why:** Single choke point for factory kwargs; CI tests can assert helper contract without importing ragas if the helper is split, or document the import gate.

### 3. CI-safe regression without live Gemini

Extend `tests/evals/` with a unit that either (a) asserts requirements text no longer forces the broken combo (`datasets<4` + `ragas<0.4` if that remains incompatible), and/or (b) mocks judge construction; do **not** call Google or import ragas in CI if that remains the project law.

**Why:** Catch pin regress without nightly keys.

### 4. Docs: EXP-004 after honest re-run

After apply, operator re-runs `--live` and fills EXP-004 After with scores (or notes remaining skips). README only if pin/commands change.

## Risks / Trade-offs

- [RAGAS 0.4 API churn on `evaluate` / metric classes] → Mitigation: apply-time smoke import + one dry code path; fall back to Langchain wrapper on 0.3.x only if 0.4 is unblockable.
- [datasets major bump on laptop] → Mitigation: operator-only extra; not API image.
- [GOOGLE_API_KEY warning when GEMINI_API_KEY also set] → Mitigation: acceptable noise; do not clear product key; optional note in setup text.
- [ret-05 still SKIP] → Mitigation: out of scope; n=4 scores still valid for EXP-004.

## Migration Plan

1. Update pins + judge wiring; land CI-safe pin/test checks.
2. Operator: `pip install -r evals/requirements-ragas.txt` (reinstall), then `--live` with JWT.
3. Paste scores into EXP-004.
4. Rollback: revert pin + script helper; product unchanged.

## Open Questions

None blocking. Exact lower/upper version bounds confirmed at apply with a dry-run install on the operator Python.
