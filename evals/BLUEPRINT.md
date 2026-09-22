# Eval lifecycle blueprint

Canonical eval program for DashNoteSystem. All eval code and datasets live under `evals/`. This file is the map later implementation changes follow.

**This is not a production SLO.** Judge scores are `lab` or `pre-deploy` records.  
**This is not** [`docs/documentation/blueprint/slice8_eval.md`](../docs/documentation/blueprint/slice8_eval.md) — that file is Slice 8X.2 Cursor prompts for the C-gate harness. Do not rewrite it.

**Phase 0 (this file) is done.** L0 fixture-gate, L1 live contract, L2 LLM-as-judge, and **L3 production observability** (Langfuse traces, Prometheus, `POST /ai/feedback`) are done. Thresholds / baseline, generator style work, and agent answer goldens remain later.

How to run what exists today: [`README.md`](README.md).

**L0/L1 alignment:** Both modes share the same `evals/golden/` corpus and the same marker / isolation / trajectory scorers. Fixtures under `evals/fixtures/` are the **recorded** form of that contract for PR CI. Live mode proves eligible (`mode_hint` `either` / `live`) cases against a real API. Fixture-only cases and unwired live trajectories SKIP in L1 — they are not a second corpus. L3 does **not** replace this contract.

**L1/L2 alignment:** L2 collects `POST /ai/chat` answers on the same JWT `wid` tenancy, seed/marker ID law, and Compose/staging target class as L1. Prefer a stack already proven by L1. If Gemini 429 blocks product chat/embed during collection, use NVIDIA NIM (different free/catalog model) via `LLM_MODEL` / `LLM_MODEL_FALLBACKS` and recreate `api` + `worker` — same hatch as L1. L2 does **not** replace L0/L1 PASS/FAIL scoring; it adds GEval answer quality.

**L2/L3 alignment:** L3 serving observability uses the same JWT `wid` tenancy as L1/L2 for traces and `POST /ai/feedback`. L0/L1 remain the retrieval/tenant `PASS: X/Y` contract. L2 remains the pre-deploy GEval suite and stays off `/ai/chat` and `/ai/agent`. L3 MUST NOT replace those scores with traces or thumbs. Sampled Langfuse faithfulness (`run_langfuse_faithfulness.py`) stays operator/nightly. Traces and thumbs are **not** production SLOs.

---

## Eval paradox / placement

You need evals to ship safely. Lab goldens are not production traffic. If you only optimize the golden set, CI is green while users get wrong answers. If you only watch HTTP 5xx, quality failures stay invisible (`200` + hallucinated answer).

**Placement that keeps the program production-grade without putting a judge on the VPS request path:**

| Layer | Where it runs | Why |
|-------|----------------|-----|
| L0 fixture | **PR CI** | Deterministic, no paid keys, no flake from quota |
| L1 live contract | Operator / nightly vs Compose or staging | Same goldens against a real API |
| L2 LLM-as-judge | **Local / pre-deploy / nightly** | Real numbers (correctness, completeness, style) before promote |
| L3 observability | Production serving | Traces and health; **never** await a judge to return `/ai/chat` or `/ai/agent` |

Enterprise/startup practice is this split — not “GEval on every user request” and not “DeepEval on every PR.”

---

## Four layers

```
┌─────────────────────────────────────────────────────────────────┐
│ L0  Fixture / golden contract     run_eval.py --mode fixture    │
│     markers · tenant · trajectories                             │
│     DONE  · PR CI  · deterministic  · no judge                  │
├─────────────────────────────────────────────────────────────────┤
│ L1  Live API contract             run_eval.py --mode live       │
│     same goldens + scorers vs Compose / staging                 │
│     DONE  · operator / nightly  · PASS: X/Y, not GEval          │
├─────────────────────────────────────────────────────────────────┤
│ L2  LLM-as-judge quality          run_quality.py                │
│     DeepEval GEval: correctness · completeness · style          │
│     DONE  · frozen answer goldens  · pre-deploy · not CI        │
├─────────────────────────────────────────────────────────────────┤
│ L3  Production observability      Langfuse + Prom + feedback    │
│     traces, empty_retrieval, thumbs                             │
│     DONE  · NEVER await a judge on /ai/chat or /ai/agent        │
└─────────────────────────────────────────────────────────────────┘
```

**Commands today vs planned**

| Layer | Command | Status |
|-------|---------|--------|
| L0 | `python evals/run_eval.py --mode fixture` | Done — PR blocking |
| L1 | `python evals/run_eval.py --mode live --base-url … --token …` | Done — operator / nightly |
| L2 | `python evals/run_quality.py` | Done — local / pre-deploy; not PR CI |
| L3 | Langfuse UI + `POST /ai/feedback`; Prometheus `/metrics` | Done — serving path has no judge |

**PR CI MUST stay L0 only.** L1 MUST NOT be a merge gate. L2 MUST stay off the hot path. Production serving MUST NOT require the judge suite to return an answer.

Optional later: a scheduled nightly/pre-deploy job with secrets. Still not a PR merge gate.

---

## Module layout

All eval artifacts live under `evals/`. Do not keep the sole copy of goldens under `src/`. Do not add the judge extra to the API image, worker image, Compose runtime, or VPS as a serving dependency.

```
evals/
  BLUEPRINT.md                 # this file (canonical lifecycle)
  README.md                    # how to run what exists
  run_eval.py                  # L0 / L1 — keep as C-gate
  run_quality.py               # L2 — DeepEval GEval (laptop)
  run_ragas.py                 # optional lab until a later change folds/retires it
  run_langfuse_faithfulness.py
  requirements-quality.txt     # DeepEval extra — laptop only
  requirements-ragas.txt       # keep until retired
  golden/
    retrieval.jsonl            # exists — marker / hit goldens
    tenant_isolation.jsonl     # exists
    agent_trajectory.jsonl     # exists — L0 tool constraints, not L2 answers
    rag_answers.jsonl          # L2 — RAG expected answers (AI-drafted/curated)
    agent_answers.jsonl        # PLANNED — later phase
  fixtures/                    # recorded L0 responses
  reports/                     # optional dated local dumps; no secrets
```

---

## Data contracts

Two different golden kinds. Do not treat retrieval markers as expected answers.

| Kind | File | Proves | Layer |
|------|------|--------|-------|
| Retrieval / tenant | `golden/retrieval.jsonl`, `tenant_isolation.jsonl` | Hits contain markers; isolation | L0 / L1 |
| Agent trajectory | `golden/agent_trajectory.jsonl` | `required_tools` / `forbidden_tools` / `sequence_mode` | L0 |
| RAG answers | `golden/rag_answers.jsonl` | Answer quality vs gold | L2 |
| Agent answers | `golden/agent_answers.jsonl` | Agent answer quality | Later phase (planned) |

### RAG answer schema (`rag_answers.jsonl`)

One JSON object per line:

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Stable case id (`rag-ans-01-…`) |
| `theme` | yes | `rag_answer` |
| `surface` | yes | `POST /ai/chat` |
| `query_text` | yes | User question |
| `expected_output` | yes | Gold answer (prose) and/or key facts |
| `completeness_checklist` | yes | Points the answer MUST cover |
| `style_notes` | no | Voice / citation / concision constraints |
| `seed` | live | `{ title, content, is_private, wait_embed_sec }` — same law as retrieval goldens |
| `fixture_ref` | fixture | Recorded chat payload if L0-for-answers is added later (not required for L2 v1) |

**Seed / fixture ID law:** do not hard-code `note_id` / `chunk_id` that only exist in one environment. Prefer `seed` or recorded fixtures. Reuse retrieval marker notes as seeds where possible.

First L2 set: about **10–20** cases, not hundreds. Surface for phase 1 is **`POST /ai/chat` only**. Do not replace chat with agent to simplify evals. Existing trajectory goldens stay L0; they are not the DeepEval answer suite.

---

## Metric suite

L2 engine: **DeepEval `GEval`** (criteria or `evaluation_steps`) with Gemini as judge. Optional later: DeepEval `FaithfulnessMetric` if we fold RAGAS grounding into the same CLI.

| Metric | Judge input | Gate (L2) | Role |
|--------|-------------|-----------|------|
| **Correctness** | actual vs `expected_output` | Hard floor (example **0.7**; tune in phase 2) | Facts match gold |
| **Completeness** | actual vs `completeness_checklist` | Hard floor (same class) | Required points present |
| **Style** | actual vs product voice rubric | **Always report**; loose or no floor at first | Control loop for generator prompts |
| Faithfulness | actual vs `retrieval_context` | Optional; not required for phase 1 | Grounding |

**Style may score low on v1.** That is an honest outcome, not a reason to omit the metric. Raising style by editing the generator prompt is later work, measured again by L2. Agent-answer goldens stay a later phase. Do not change `RAG_SYSTEM_INSTRUCTION` just to lift a style mean.

Concrete style rubric (answer string only): concise; no invented facts; preserve marker tokens from the retrieved notes; the product refusal sentence is the allowed non-answer. Do not require citation prose inside the answer. Citations stay a sibling field of the chat response.

**Judge scale:** GEval’s default integer range is 0–10, then divided by 10. Steps must not say “score from 0 to 1”. Each run replaces `evals/quality_scores.jsonl` and renders `evals/eval_report_2.md` from it. `evals/eval_report.md` is the historical scale-collapsed paste, not the record of a later run.

**These scores are not production SLOs.** Label runs `lab` or `pre-deploy`.

---

## Single quality CLI (planned)

**Command (L2):**

```powershell
$env:PYTHONPATH = "src"
pip install -r evals/requirements-quality.txt
python evals/run_quality.py --token "<access_token>" --base-url http://127.0.0.1
```

Optional flags (add to the same command; do not paste `>>` comment lines into PowerShell): `--limit N` (smoke path), `--timeout 300`, `--judge-backend nim` (default, `gpt-oss-20b`), `--judge-backend gemini` (opt-in), `--seed-live`. Never embed a live JWT in this file.

One runner. Do not add a second DeepEval entrypoint. Do not import DeepEval from `run_eval.py`.

**Intended flow**

```
run_quality.py
    │
    ├─ load judge key (fail closed)
    ├─ load rag_answers.jsonl (optional --limit)
    ├─ for each case: POST /ai/chat with JWT (message only; wid from token)
    │     collect actual_output + retrieval_context texts
    │     SKIP on non-200, empty answer, empty retrieval, HTTP timeout,
    │     or other request-transport failure (count SKIPs; remaining cases still run)
    ├─ DeepEval evaluate(test_cases, metrics)
    └─ print per-case + aggregate scores; exit 0 only if
         n>0, required metrics numeric, hard floors met
```

**Terminal output MUST include:** environment label, judge model, per-metric aggregates (correctness, completeness, style), collected `n`, SKIP count and reasons, NaN notes.

**Fail closed**

- Missing/blank judge key → non-zero exit; name the env var; **never** fall back to `GEMINI_API_KEY`
- Zero scored rows → non-zero exit; **do not** print fabricated aggregate scores
- Required metrics all NaN / non-numeric → non-zero exit; do not invent means
- Timed-out `POST /ai/chat` (or follow-up search) → **SKIP**, not an uncaught traceback. All-timeout SKIPs still fail-closed (`n=0`). Uncaught timeout traceback is a harness bug. `--limit` is the smoke path on a slow NIM stack.

---

## Judge + secrets

| Key | Use |
|-----|-----|
| `GEMINI_API_KEY` | Product embeddings / chat fallback — **not** the judge |
| `GEMINI_API_KEY_2` (or documented successor) | L2 judge and existing RAGAS lab only |

- Laptop / operator env only. Placeholder may live in `.env.example`.
- Must **not** be required by API Settings, Compose product env, or VPS `.env`.
- Must **not** be copied into the API image.
- Default L2 judge: NVIDIA NIM `nvidia_nim/openai/gpt-oss-20b` (`--judge-backend nim`) — a different catalog id from product Lightning. Opt-in Gemini: `--judge-backend gemini` with `GEMINI_API_KEY_2`. Quota / timeout / 429 are expected failure modes — fail closed, do not invent scores.
- **L0 fixture needs no LLM keys.** Gemini 429 on later live collection or product chat is an operator concern: walk to NVIDIA NIM with a different free/catalog model (`LLM_MODEL_FALLBACKS`, e.g. `nvidia_nim/openai/gpt-oss-20b` before Gemini Flash). That hatch MUST NOT await a judge on `/ai/chat` or `/ai/agent`, and MUST NOT be required to green PR CI.

**L3 Langfuse env (serving, not a judge):** `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` enable the client. Canonical host is `LANGFUSE_HOST`. Production-shaped files MAY set `LANGFUSE_BASE_URL` instead — Settings treats it as an alias when `LANGFUSE_HOST` is blank. Soft: missing keys do not fail `/health` or `/ai/chat`. Never paste live keys into this file. How to confirm traces and feedback: [`README.md`](README.md).

---

## Tenancy

Live L1 and live L2 collection authenticate with a JWT. Retrieval scope is that token’s workspace (`wid`) only. L3 traces and `POST /ai/feedback` use the same JWT `wid` — never a workspace id from the body for scoping.

- `POST /ai/chat` body: `message` only (plus existing product fields). **No** workspace id from query or body for scoping.
- Forged workspace fields must not expand retrieval.
- Tenant-isolation goldens (`tenant_isolation.jsonl`) remain the **C-gate proof**. The judge suite does not replace them.

---

## Gold lifecycle

```
v0  AI-drafted Q / expected_output / checklist
        │
        ▼
    freeze case ids
        │
        ▼
    human curate as failure modes appear
        │
        ▼
    regression: same ids, compare to last baseline (phase 2)
```

**Honesty:** call v0 goldens **AI-drafted, then curated**. Do not claim expert-labeled from day one.

**Teacher bias:** if the same model family writes goldens and generates answers, correctness can look artificially high. Mitigations: human spot-check a slice, gold as checklists not only prose, optionally a different judge family later.

---

## CI / pre-deploy / production

```
PR merge ──▶ L0 fixture (ci.yml) ──▶ green without judge keys
                    │
pre-deploy / nightly ──▶ L2 quality CLI (planned; local Compose)
                    │     fail closed on n=0 / NaN / hard-floor miss
                    ▼
              promote / deploy
                    │
production ──▶ L3 traces + feedback + Prom
                    │     no GEval on the request
                    ▼
              EXPERIMENTS if a quality loop ships
```

| Environment | Runs | Blocking? |
|-------------|------|-----------|
| GitHub PR CI | L0 fixture | Yes |
| Operator laptop | L1 live, L2 quality, RAGAS lab, Langfuse seed | No (today) |
| Pre-deploy | L2 `run_quality.py` | Yes for *promote*, not for *merge* |
| VPS serving | L3 only | Judge must not be in the request path |

---

## Phased roadmap

Each phase is a **separate OpenSpec change** unless an operator explicitly expands scope.

| Phase | Ships | Status |
|-------|--------|--------|
| **0** | This blueprint + README / doc pointers | Done |
| **1** | L0 fixture-gate close-out: scoring tests, honest recorded `PASS: X/Y`, NVIDIA NIM as Gemini 429 hatch | Done |
| **2** | L1 live contract: same goldens/scorers vs Compose/staging, L0/L1 alignment docs, honest live `PASS: X/Y`, NIM hatch when Gemini 429 blocks live | Done |
| **3** | `rag_answers.jsonl` (AI-drafted), `run_quality.py`, `requirements-quality.txt`, CI-safe helper tests only | Done |
| **4** | L3 production observability: Langfuse env alias, traces + feedback + Prom docs, apply proof, L0/L1 re-alignment | Done |
| **5** | Thresholds, baseline comparison, dated EXPERIMENTS row from a real local run | Later |
| **6** | Generator / prompt / citation work driven by style scores (product code; still measured by L2) | Later |
| **7** | `agent_answers.jsonl` + same CLI theme; trajectories stay L0/L1 fixture-primary | Later |
| **8** | Optional nightly/pre-deploy workflow with secrets — still not PR-blocking | Later |

Do not implement thresholds, agent answers, or nightly judge CI in the same change as L3.

---

## Honesty + EXPERIMENTS

Every recorded L2 (and current RAGAS) run MUST include:

- environment = `lab` or `pre-deploy` (or `live-local` for L1)
- judge model
- `n`
- SKIP count and reasons
- NaN notes

A lone `1.0` without `n` is not evidence. Zero collected rows is not a successful faithfulness or GEval run.

Ledger: [`docs/EXPERIMENTS.md`](../docs/EXPERIMENTS.md). Interview RAGAS pack (until superseded): [`docs/ragas-lab-report.md`](../docs/ragas-lab-report.md).

---

## What exists today

Keep these until a later change **explicitly** folds or retires them. C-gate is not optional.

| Piece | Role |
|-------|------|
| `run_eval.py --mode fixture` | Hire / PR C-gate. Last recorded **PASS: 20/20** (see README). |
| `run_eval.py --mode live` | L1 operator/nightly contract vs real API (same goldens/scorers as L0) |
| `run_quality.py` | L2 DeepEval GEval on `rag_answers.jsonl` (laptop / pre-deploy; `GEMINI_API_KEY_2`) |
| `run_langfuse_faithfulness.py` | Operator sampled faithfulness (Langfuse UI) |
| `run_ragas.py` | Laptop RAGAS lab (faithfulness / context precision, `GEMINI_API_KEY_2`) |
| Langfuse traces + `POST /ai/feedback` + Prom `dashnote_ai_*` | L3 serving observability — not a merge gate, not a production SLO |

RAGAS and Langfuse labs are thickeners, not SLOs, not PR CI. They MAY later fold into DeepEval (e.g. `FaithfulnessMetric`). A later change must explicitly fold or retire them.

---

## Non-goals

- Do not collapse `/ai/chat*` and `/ai/agent*`
- Do not put LLM-as-judge on the hot path
- Do not make DeepEval a PR merge gate
- Do not add judge libraries to the API image or VPS serving stack
- Do not move eval data outside `evals/`
- Do not rewrite `slice8_eval.md`
- Do not call GEval or RAGAS means production SLOs
- Do not treat agent trajectory goldens as the L2 answer suite
- Do not implement the whole program in one change
