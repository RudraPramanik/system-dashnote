## Why

The RAGAS operator lab is wired and EXP-004 already records a partial `n=2` smoke (faithfulness / context_precision = 1.0), but the latest `--live` run collected **zero** rows (every golden `POST /ai/chat` returned HTTP 500). That leaves no hire-ready, showable evidence pack: interviewers see either a failed terminal dump or an unexplained perfect score on a tiny sample. We need a **production-grade lab evidence loop**—healthy collection when the local stack is up, honest metrics, and a shareable report that frames RAGAS as an operator/nightly thickener (not a production SLO or CI gate).

## What Changes

- Add a **preflight / failure-mode path** for the live RAGAS lab: detect unreachable API vs chat 500 vs empty retrieval vs missing judge key, and document how operators unblock collection before scoring.
- Re-run (or re-attempt) `evals/run_ragas.py --live` against local Compose once chat is healthy enough to collect ≥1 scored row; record dated results with `n`, SKIP reasons, judge model, and environment=`lab`.
- Produce an **interview-shareable RAGAS lab report** (Markdown under `docs/` or `evals/`) covering architecture (fixture C-gate vs lab judge), procedure, results table, caveats, and security hygiene (no JWT/API keys in the report or screenshots).
- Update `docs/EXPERIMENTS.md` EXP-004 (and light pointers from `evals/README.md` / interview talk track) so the report and experiment record stay consistent.
- Optionally harden `run_ragas.py` output so “no rows / all SKIP” is clearly distinguished from printed metric scores (exit non-zero already; messaging may clarify for operators).
- **Non-goals / boundaries:** Do **not** add RAGAS to PR CI, VPS, Compose API image, or Prometheus SLOs. Do **not** require DeepEval. Do **not** replace the golden fixture harness. Browser UI automation is out of scope (lab remains terminal → local API; Langfuse UI remains the separate faithfulness path).

## Capabilities

### New Capabilities

- `interview-evidence`: Hire/portfolio evidence pack for the RAGAS lab—shareable report artifact, honest lab metrics with caveats, secrets hygiene, and discoverability from eval/interview docs.

### Modified Capabilities

- `ai-eval-harness`: Live RAGAS collection MUST surface actionable failure modes when chat/search cannot yield rows; operators MUST be able to record a dated lab run (or an honest blocked-by-product note) and MUST keep RAGAS off CI/VPS/product hot path; EXPERIMENTS remains the dated lab ledger.

## Impact

- **Code (optional, minimal):** `evals/run_ragas.py` / `evals/ragas_lab.py` messaging or preflight helpers; CI-safe unit tests only if helpers are added (no ragas import in CI).
- **Ops:** Local Compose must be healthy for a successful live re-run; product `/ai/chat` 500s may need diagnosis/fix as a dependency of collection—not as a new production SLO.
- **Docs:** New report Markdown; `docs/EXPERIMENTS.md`; light links in `evals/README.md` and possibly `docs/interview-talk-track.md`.
- **Secrets:** Report and docs MUST NOT embed JWTs, `GEMINI_API_KEY*`, or other credentials; rotate any token previously pasted into terminals if shared.
- **Deps:** Laptop `evals/requirements-ragas.txt` only; no base/API image changes.
