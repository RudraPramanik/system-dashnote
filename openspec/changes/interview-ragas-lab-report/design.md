## Context

See `proposal.md` for motivation. The operator RAGAS path already exists (`evals/run_ragas.py`, `evals/requirements-ragas.txt`, dedicated `GEMINI_API_KEY_2`, EXP-004). Latest live attempts often die in **collection** (`POST /ai/chat` HTTP 500) before the Gemini judge runs. Fixture C-gate (`run_eval.py --mode fixture`) remains the hire minimum; this change packages a **production-grade evidence loop** around the lab without promoting RAGAS into CI/VPS/SLOs.

## Goals / Non-Goals

**Goals:**
- Make live-lab failure modes operator-obvious (collection vs judge vs missing key).
- Capture one dated, honest lab outcome in EXPERIMENTS + a shareable Markdown report.
- Keep report/interview artifacts secrets-safe and consistent with harness boundaries.

**Non-Goals:**
- Browser-driven eval automation or Playwright “RAGAS UI” tests.
- Adding RAGAS to GitHub Actions, Compose images, or Prometheus alerts.
- Full root-cause product rewrite beyond what is needed to collect ≥1 live row (or documenting the blocker if unblockable in apply).
- Replacing Langfuse sampled faithfulness with RAGAS as the primary in-product judge.

## Decisions

### 1. Report location and shape
- **Choice:** Single Markdown at `docs/ragas-lab-report.md` (portfolio-adjacent under `docs/`, linked from `evals/README.md`).
- **Why:** Interviewers browse docs; operators already live in `evals/`. One canonical file avoids drift between “portfolio” and “ops” copies.
- **Alternatives:** `evals/RAGAS_REPORT.md` only (harder for strangers); dual copies (drift); PDF/HTML (overkill).

### 2. Fresh live run vs documenting blocked collection
- **Choice:** Apply attempts, in order: (a) verify `/health` + soft `/health/ai`, (b) spot-check one `POST /ai/chat` with a placeholder JWT, (c) diagnose obvious 500 causes from API logs if all goldens fail, (d) re-run `--live`, (e) if still zero rows after reasonable unblock, ship report + EXPERIMENTS with **blocked-collection** honesty instead of inventing scores.
- **Why:** Specs require honesty; “production-grade” means credible process, not fake 1.0.
- **Alternatives:** Always paste EXP-004’s prior `n=2` without re-attempt (weaker); block the whole change until chat is perfect (too brittle for docs-first evidence).

### 3. Code vs docs-only for failure surfacing
- **Choice:** Prefer clarifying CLI messages / setup text if current SKIP lines are already specific enough; add a tiny preflight (`GET /health`) only if it materially reduces misdiagnosis. Do not import ragas into CI tests.
- **Why:** Behavior already exits non-zero on zero rows; most value is docs + report + EXPERIMENTS sync.
- **Alternatives:** Large runner rewrite; structured JSON report mode (defer unless needed).

### 4. Product chat 500 scope
- **Choice:** Treat chat 500 as a **collection dependency**. During apply, inspect logs and fix only clear, low-risk defects that unblock local lab (misconfig, missing seed, obvious bug). Defer deep RAG regressions to a separate change if not quick.
- **Why:** Proposal non-goals forbid boiling the ocean; interview evidence can still ship with an honest blocker note.
- **Alternatives:** Expand this change into a full chat reliability project (reject for scope).

### 5. Secrets hygiene
- **Choice:** Report and README snippets use `<access_token>` / env-var names only. Call out JWT rotation if tokens appeared in terminal history shared externally.
- **Why:** Spec requirement; interview artifacts are high-leak risk.
- **Alternatives:** “Redact later” (too late once shared).

### 6. Metrics narrative for interviews
- **Choice:** Lead with fixture `PASS: X/Y`, then RAGAS lab table with `n` and caveats, then point at EXP-001 empty-retrieval as the stronger measure→improve story.
- **Why:** Perfect faithfulness on tiny `n` is a weak sole claim; layered evidence matches Eval Paradox talk track.
- **Alternatives:** Lead with RAGAS 1.0 only (misleading).

## Risks / Trade-offs

- **[Risk] Chat 500s persist → Mitigation:** Ship blocked-collection report; open/follow a separate product fix; do not fabricate scores.
- **[Risk] Small `n` over-interpreted in interviews → Mitigation:** Report + talk track emphasize sample size, SKIPs, lab≠SLO.
- **[Risk] Credential leakage in report drafts → Mitigation:** Placeholder-only commands; quick grep for `eyJ` / `AIza` / `sk-` before share.
- **[Risk] Doc drift vs EXPERIMENTS → Mitigation:** One apply task updates both from the same run transcript.
- **[Trade-off] Minimal code changes →** Faster, safer apply; slightly less automated preflight until a later polish change.

## Migration Plan

1. Docs/report land in-repo only (no VPS deploy of judge path).
2. Operators reinstall `evals/requirements-ragas.txt` on laptop if needed; no API image rebuild.
3. Rollback = revert doc/report commits; lab script remains optional and unused by CI.

## Open Questions

- Exact root cause of current chat 500s (resolved during apply via logs, or recorded as blocked).
- Whether talk-track edit is a one-line pointer or a short “how to explain RAGAS” subsection (apply chooses shortest pointer that satisfies the discoverability scenario).
