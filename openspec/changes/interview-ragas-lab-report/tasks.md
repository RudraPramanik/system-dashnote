## 1. Preflight and collection health

- [x] 1.1 Confirm local Compose API is up (`GET /health`, soft `GET /health/ai`) and document any soft failures that block RAG/chat
- [x] 1.2 Spot-check one authenticated `POST /ai/chat` (placeholder token only in docs); if HTTP 500, capture API/worker log root cause
- [x] 1.3 Apply only a low-risk fix that unblocks local collection when the cause is clear; otherwise record the blocker for honest reporting (do not expand into a full chat reliability project)

## 2. Live RAGAS lab run

- [x] 2.1 Ensure operator laptop has `pip install -r evals/requirements-ragas.txt` and `GEMINI_API_KEY_2` set (never reuse product `GEMINI_API_KEY`)
- [x] 2.2 Run `python evals/run_ragas.py --live --token "<access_token>"` against local Compose; capture full transcript (case COLLECT/SKIP lines, `n`, faithfulness, context_precision, judge model)
- [x] 2.3 If zero rows collected after 1.x, stop scoring and proceed with blocked-collection evidence (no invented metrics)

## 3. CLI / docs clarity for failure modes (minimal code)

- [x] 3.1 Review `evals/run_ragas.py` / `--setup` text; clarify messaging so “no rows / chat errors” cannot be mistaken for a successful scored run (exit non-zero already required)
- [x] 3.2 Update `evals/README.md` RAGAS section with live preflight prerequisites and “collection failure ≠ judge pin failure” guidance
- [x] 3.3 Add CI-safe unit coverage only if new helpers are introduced (no ragas import / no live Google calls)

## 4. Interview report and EXPERIMENTS sync

- [x] 4.1 Create `docs/ragas-lab-report.md` with architecture (fixture C-gate vs lab judge), procedure, dated results or blocked-collection table, caveats (not SLO / not CI / not VPS), and placeholder-only commands
- [x] 4.2 Grep the report (and edited docs) for leaked JWTs / API keys; redact to placeholders; note token rotation if a live token was previously pasted in a shareable terminal
- [x] 4.3 Update `docs/EXPERIMENTS.md` EXP-004 so it matches the same dated outcome as the report (`environment=lab` or `live-local`)
- [x] 4.4 Link the report from `evals/README.md`; add a short pointer in `docs/interview-talk-track.md` if that file exists

## 5. Boundary verification

- [x] 5.1 Confirm PR CI / compat gates still do not invoke `run_ragas.py` and ragas is not added to API image / base requirements
- [x] 5.2 Re-run fixture harness `python evals/run_eval.py --mode fixture` if product chat code was touched; record `PASS: X/Y` in the report or EXPERIMENTS notes as supporting C-gate evidence
