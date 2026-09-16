## 1. Dependency pin

- [x] 1.1 Update `evals/requirements-ragas.txt` so pip resolves a Gemini-capable RAGAS (prefer `ragas>=0.4,<0.5` or apply-time verified range) and remove/relax the `datasets<4` ceiling that forced `ragas==0.3.2`
- [x] 1.2 Dry-run / install the extra on the operator Python and confirm `llm_factory` accepts `provider=` / `client=` (or document Langchain wrapper fallback if 0.4 is unblockable)

## 2. Judge wiring

- [x] 2.1 Fix Gemini judge construction in `evals/run_ragas.py` (optional small helper) so Faithfulness + ContextPrecision evaluate runs without `TypeError` on factory kwargs; keep `GEMINI_API_KEY_2` fail-closed and never assign product `GEMINI_API_KEY`
- [x] 2.2 On unsupported/mismatched install, exit non-zero with a message that points at reinstalling `evals/requirements-ragas.txt`

## 3. Tests (CI-safe)

- [x] 3.1 Add/extend `tests/evals/` coverage so the broken pin combo cannot silently return (assert requirements constraints and/or judge-build contract) without importing ragas or calling Google in CI
- [x] 3.2 Confirm `tests/observability/test_compat_gate.py` (or sibling) still ensures CI does not invoke `run_ragas.py`

## 4. Docs and operator verify

- [x] 4.1 Touch `evals/README.md` only if install/pin/commands changed
- [x] 4.2 Re-run `python evals/run_ragas.py --live --token …` against local Compose; record faithfulness + context_precision in `docs/EXPERIMENTS.md` EXP-004 (`environment=lab`), noting any SKIP rows (e.g. ret-05 500) without treating scores as an SLO
