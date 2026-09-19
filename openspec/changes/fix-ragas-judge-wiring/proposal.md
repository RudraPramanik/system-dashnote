## Why

The operator RAGAS lab (`evals/run_ragas.py --live`) collects chat+search triples successfully but crashes before scoring: installed `ragas` 0.3.2’s `llm_factory` rejects `provider=` / `client=`, so faithfulness and context precision never print. EXP-004 stays “pending first scores” until the laptop extra pins a Gemini-capable RAGAS and the runner wires the judge in a way that actually evaluates.

## What Changes

- Fix `evals/requirements-ragas.txt` so pip resolves a RAGAS release that supports Google/`llm_factory(..., provider="google", client=...)` (today `datasets<4` forces a walk-down to 0.3.2).
- Fix judge construction in `evals/run_ragas.py` (and a small CI-safe helper if needed) so `--live` completes and prints aggregate faithfulness + context precision.
- Keep fail-closed `GEMINI_API_KEY_2` (never fall back to `GEMINI_API_KEY`); keep lab off CI / VPS / API image.
- Update operator docs / EXP-004 notes only as needed for the pin and re-run command.
- **Out of scope:** diagnosing `ret-05` chat HTTP 500 (product path); may still SKIP that row. Not a production SLO.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-eval-harness`: Operator RAGAS `--live` MUST complete judge evaluation with the dedicated Gemini key and print aggregate faithfulness + context precision when collection yields ≥1 row; dependency pins MUST resolve to a Gemini-capable RAGAS; fixture C-gate and VPS boundaries unchanged.

## Impact

- **Code:** `evals/run_ragas.py`, optionally `evals/ragas_lab.py`, `evals/requirements-ragas.txt`, CI-safe tests under `tests/evals/`.
- **Deps (laptop only):** ragas / datasets pin range change in the operator extra — not `requirements/base.txt`, not Compose images.
- **APIs / tenancy:** none; live collection still JWT-only, no workspace in body.
- **Docs:** light touch on `evals/README.md` and/or `docs/EXPERIMENTS.md` EXP-004 after a successful lab run (or honest “still blocked” note if apply cannot run live).
- **Non-goals:** DeepEval; Prometheus RAGAS SLOs; chasing unrelated `/ai/chat` 500s; collapsing chat vs agent.
