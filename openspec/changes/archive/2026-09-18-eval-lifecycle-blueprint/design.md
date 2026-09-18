## Context

See `proposal.md` for motivation. Today `evals/` already has:

- C-gate: `golden/*.jsonl`, `fixtures/`, `run_eval.py` (fixture + live) — PR CI wired
- Operator labs: `run_ragas.py`, `run_langfuse_faithfulness.py` — laptop only, dedicated `GEMINI_API_KEY_2`
- Retrieval goldens are **marker/hit** cases, not answer goldens (`expected_output` / fact checklists)

`docs/documentation/blueprint/slice8_eval.md` is the Slice 8X.2 **Cursor prompt** history for that C-gate. Do not replace or rewrite it. The new artifact is an operator lifecycle map at `evals/BLUEPRINT.md`.

This change is **docs-only**. Later OpenSpec changes implement phases in order.

## Goals / Non-Goals

**Goals:**

- Publish one canonical blueprint that a later implementer can follow without re-litigating architecture
- Encode production-grade eval practice (startup/enterprise) in repo-shaped layers, not generic ML-platform theater
- Specify modular `evals/` layout, data contracts, DeepEval metric suite, single quality CLI, and placement (CI vs pre-deploy vs prod)
- Keep chat ≠ agent, JWT tenancy, and fixture CI as laws

**Non-Goals:**

- Implementing DeepEval, answer goldens, or a new runner in this change
- Adding judge libraries to the API image, Compose, VPS, or PR CI
- Collapsing `/ai/chat*` into `/ai/agent*`
- Replacing Langfuse traces or Prometheus health with judge scores
- Treating RAGAS scores or GEval means as production SLOs
- Rewriting `slice8_eval.md`

## Decisions

### 1. Blueprint lives at `evals/BLUEPRINT.md`

**Choice:** Module-root Markdown beside the runners, not under `docs/documentation/blueprint/`.

**Why:** Eval code, data, and program law stay in one tree (`evals/`). Slice blueprints under `docs/documentation/blueprint/` are Cursor implementation prompts; mixing them would confuse “how we built C-gate” with “how quality works going forward.”

**Alternative:** `docs/eval-lifecycle.md` — rejected; user asked for eval + eval data under `evals/`.

**Apply:** Write `evals/BLUEPRINT.md` using the outline in Decision 8. Add a short “Eval lifecycle” pointer at the top of the Post-C-gate section in `evals/README.md`. Optional one-line pointer from `docs/EXPERIMENTS.md` intro and `docs/interview-talk-track.md` Eval Paradox paragraph — only if it stays a pointer, not a second copy of the blueprint.

### 2. Four layers, never one harness

```
┌─────────────────────────────────────────────────────────────────┐
│ L0  Fixture / golden contract     run_eval.py --mode fixture    │
│     markers · tenant · trajectories                             │
│     PR CI  · deterministic  · no judge                          │
├─────────────────────────────────────────────────────────────────┤
│ L1  Live API contract             run_eval.py --mode live       │
│     same goldens vs local Compose / staging                     │
│     operator / nightly  · still pass/fail, not GEval            │
├─────────────────────────────────────────────────────────────────┤
│ L2  LLM-as-judge quality          single evals/ runner (later)  │
│     DeepEval GEval: correctness · completeness · style          │
│     frozen answer goldens  · pre-deploy / nightly  · not PR     │
├─────────────────────────────────────────────────────────────────┤
│ L3  Production observability      Langfuse + Prom + feedback    │
│     traces, empty_retrieval, thumbs                             │
│     NEVER await a judge on /ai/chat or /ai/agent                │
└─────────────────────────────────────────────────────────────────┘
```

**Why:** This is the enterprise split (deterministic tests vs sampled/offline judges vs production telemetry). Merging L2 into PR CI recreates the Eval Paradox (flaky keys, quota, false greens). Merging L2 into the request path is a latency/cost bug, not “production-grade.”

**Alternative:** DeepEval on every PR — rejected. Optional later: scheduled nightly workflow with secrets, still not a merge blocker.

### 3. Modular `evals/` target layout (implement later; document now)

```
evals/
  BLUEPRINT.md                 # this change
  README.md                    # how to run (keep; add pointer)
  run_eval.py                  # L0/L1 — keep forever as C-gate
  run_quality.py               # L2 planned single CLI (name locked here)
  run_ragas.py                 # keep until a later change folds/retires
  run_langfuse_faithfulness.py
  requirements-quality.txt     # DeepEval extra (later; laptop only)
  requirements-ragas.txt       # keep until retired
  golden/
    retrieval.jsonl            # existing marker goldens
    tenant_isolation.jsonl
    agent_trajectory.jsonl
    rag_answers.jsonl          # L2 RAG expected answers (later)
    agent_answers.jsonl        # later phase
  fixtures/                    # recorded L0 responses
  reports/                     # optional dated local dumps; no secrets
```

**Single CLI law:** `python evals/run_quality.py` (plus documented flags: `--token`, `--base-url`, `--limit`) is the one-shot collect → judge → terminal score path. Do not add a second DeepEval entrypoint. Do not make `run_eval.py` import DeepEval.

**Why `run_quality.py` not `run_deepeval.py`:** Framework can be swapped; the operator command should name the *job* (quality suite), not the library. Blueprint still names DeepEval as the chosen L2 engine.

**Alternative:** One mega `run_eval.py` with `--mode deepeval` — rejected. C-gate must stay import-light for CI.

### 4. DeepEval GEval as L2 engine; RAGAS stays optional lab

**Choice:** Correctness / completeness / style via DeepEval `GEval` (criteria or `evaluation_steps`, `expected_output` / checklist). Optional later: DeepEval `FaithfulnessMetric` if we want grounding without keeping a second RAGAS pin.

**Judge:** Dedicated key only (`GEMINI_API_KEY_2` or documented successor). Default judge model can match the lab (`gemini-3.6-flash`) with `--judge-model` override. Fail closed; never fall back to `GEMINI_API_KEY`.

**Why DeepEval over expanding RAGAS:** Rubric metrics (especially style) are GEval’s job; RAGAS is retrieval-faithfulness shaped; interviews/enterprises recognize DeepEval for LLM-as-judge suites.

**Alternative:** Custom JSON rubric script — more control, worse recognizability. Rejected for L2 v1.

**RAGAS:** Keep documented until a later change explicitly folds faithfulness into DeepEval or archives the lab.

### 5. Metric policy

| Metric | Judge input | Gate (L2) | Role |
|--------|-------------|-----------|------|
| Correctness | actual vs `expected_output` | Hard floor (document example 0.7; tune later) | Factual vs gold |
| Completeness | actual vs checklist / expected points | Hard floor (same class) | Required facts present |
| Style | actual vs product voice rubric | Report always; loose or no floor at first | Control loop for generator prompts |
| Faithfulness | actual vs `retrieval_context` | Optional; not required for phase 2 | Grounding |

Style scoring low on v1 goldens is **expected**. Raising it is a **generator** change (prompt/citation policy), tracked in EXPERIMENTS, not a reason to drop the metric.

Every printed/recorded run MUST include: environment label (`lab` / `pre-deploy`), judge model, `n`, SKIP count/reasons, NaN notes. Zero rows or all-NaN required metrics → non-zero exit, no fabricated means.

### 6. Answer golden schema (RAG first)

Planned `evals/golden/rag_answers.jsonl` records (one JSON object per line):

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Stable case id (`rag-ans-01-…`) |
| `theme` | yes | `rag_answer` |
| `surface` | yes | `POST /ai/chat` |
| `query_text` | yes | User question |
| `expected_output` | yes | Gold answer (prose) and/or key facts |
| `completeness_checklist` | yes | List of points the answer MUST cover |
| `style_notes` | no | Voice / citation / concision constraints |
| `seed` | live | `{ title, content, is_private, wait_embed_sec }` — same law as retrieval goldens |
| `fixture_ref` | fixture | Recorded chat payload if we add L0 for answers later (not required for L2 v1) |

Reuse retrieval marker notes as seeds where possible so live workspaces stay small. Do **not** hard-code `note_id` / `chunk_id`.

**v0 goldens:** AI-drafted is allowed. Blueprint MUST say: synthetic seed, then human-curate as failure modes appear; watch teacher bias (same model family writing gold and generating answers). Target first L2 set: ~10–20 cases, not hundreds.

Agent answer goldens wait for the agent phase. Existing `agent_trajectory.jsonl` stays L0.

### 7. Quality CLI behavior (specified now, coded later)

Intended flow:

```
run_quality.py
    │
    ├─ load judge key (fail closed)
    ├─ load rag_answers.jsonl (optional --limit)
    ├─ for each case: POST /ai/chat with JWT (message only; wid from token)
    │     collect actual_output + retrieval_context texts
    │     SKIP on non-200, empty answer, or empty retrieval (count SKIPs)
    ├─ DeepEval evaluate(test_cases, metrics)
    └─ print per-case + aggregate scores; exit 0 only if
         n>0, required metrics numeric, hard floors met
```

Live HTTP: `message` only on chat; no workspace in body. Same tenancy law as RAGAS lab.

### 8. Required sections of `evals/BLUEPRINT.md`

Apply MUST include these headings (wording may vary; content MUST match specs):

1. **Purpose** — canonical lifecycle; not an SLO; not slice8 Cursor prompts
2. **Eval paradox / placement** — why L0 stays in CI and L2 stays pre-deploy
3. **Four layers** — diagram + which commands exist today vs planned
4. **Module layout** — target `evals/` tree
5. **Data contracts** — retrieval vs answer goldens; schema table; seed/fixture ID law
6. **Metric suite** — correctness, completeness, style, optional faithfulness; hard vs soft gates; style-as-lever
7. **Single quality CLI** — command, outputs, fail-closed, flags
8. **Judge + secrets** — dedicated key, not in API Settings / VPS / product Gemini
9. **Tenancy** — JWT `wid`; isolation remains C-gate
10. **Gold lifecycle** — AI draft → curate; teacher bias; freeze ids for regression
11. **CI / pre-deploy / production** — what runs where; nightly optional later
12. **Phased roadmap** — see Decision 9
13. **Honesty + EXPERIMENTS** — `n`, SKIP, NaN; lab label; link EXPERIMENTS
14. **What exists today** — fixture 20/20, RAGAS lab, Langfuse path — keep until superseded
15. **Non-goals** — chat≠agent, no judge on hot path, no PR DeepEval

Keep the blueprint readable in one sitting. Prefer diagrams and tables over essay.

### 9. Phased roadmap (separate OpenSpec changes)

| Phase | Change | Ships |
|-------|--------|-------|
| 0 | **This change** | `evals/BLUEPRINT.md` + README (+ optional doc pointers) |
| 1 | RAG quality suite | `rag_answers.jsonl` (AI-drafted), `run_quality.py`, `requirements-quality.txt`, CI-safe tests for helpers only |
| 2 | Gates + regression | Thresholds, baseline comparison, dated EXPERIMENTS row from a real local run |
| 3 | Style loop | Generator/prompt/citation work driven by style scores (product code; still measured by L2) |
| 4 | Agent quality | `agent_answers.jsonl` + same CLI theme; trajectories stay L0 |
| 5 | Optional automation | Nightly/pre-deploy workflow with secrets — still not PR-blocking |

This apply stops at phase 0.

### 10. CI-safe tests for this change

Docs-only: no pytest required unless a helper is added (it should not be). Do not import DeepEval in CI.

## Risks / Trade-offs

- **[Risk] Blueprint bit-rots while code lags** → Mitigation: phases are explicit; README states “planned vs exists”; next change is phase 1 only.
- **[Risk] Two blueprints (`slice8_eval.md` vs `evals/BLUEPRINT.md`)** → Mitigation: each file’s purpose statement; README points at both with different jobs.
- **[Risk] Naming `run_quality.py` before it exists confuses operators** → Mitigation: blueprint marks it **planned**; README does not document a fake command as runnable.
- **[Risk] AI goldens inflate correctness** → Mitigation: document teacher bias; later human curate; optional different judge family.
- **[Risk] Style metric noise** → Mitigation: concrete rubric (citations, concision, no invented certainty); soft gate until generator work.
- **[Trade-off] DeepEval extra vs thin custom judge** → Extra is heavier on the laptop; we accept that to get a standard GEval suite. Extra never enters the API image.
- **[Trade-off] Keeping RAGAS + DeepEval temporarily** → Duplicate judge cost; honesty beats a forced migration in phase 0.

## Migration Plan

1. Add `evals/BLUEPRINT.md`.
2. Link from `evals/README.md` (Post-C-gate section, above RAGAS).
3. Optional pointer from EXPERIMENTS / interview talk track.
4. No runtime deploy, no rollback beyond reverting the Markdown.
5. Do not archive or delete RAGAS/Langfuse docs in this change.

## Open Questions

None that block this docs change. Judge model id and exact numeric floors are tuned in phase 1–2 against a real local run.
