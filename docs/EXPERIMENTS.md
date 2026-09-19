# EXPERIMENTS — measure → improve

Canonical before/after record for DashNoteSystem quality and cost experiments.
Does **not** replace the golden harness (`evals/run_eval.py`). Fixture CI stays
deterministic; live judges stay operator/nightly. Eval program map: [`evals/BLUEPRINT.md`](../evals/BLUEPRINT.md).

**Template (copy for new rows):**

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Environment | fixture \| live-local \| lab |
| Baseline | signal before change |
| Change | what we changed |
| After | signal after change |
| Notes | caveats |

---

## EXP-001 — Empty retrieval: stop hallucinated answers

| Field | Value |
|-------|-------|
| Date | 2026-09-13 |
| Environment | fixture (+ code path in `RagService`) |
| Baseline | **Failure mode:** empty retrieval still calling the LLM → risk of confident invented answers while HTTP stayed 200 (quality error invisible to Grafana 5xx). No golden asserting empty-hit behavior. |
| Change | Skip LLM generation on empty retrieval; return honest fallback (`EMPTY_RETRIEVAL_ANSWER`); attach Langfuse `empty_retrieval` score; golden `ret-08-irrelevant-emptyish` expects **0** hits (`evals/fixtures/ret-08-empty.json`). |
| After | Fixture harness **PASS: 20/20** including `ret-08` (recorded 2026-09-07; re-verified during interview-proof-slices apply). Empty queries no longer pay for a generation call (see cost sample in README / below). |
| Notes | This is a harness-linked quality loop, not a live faithfulness judge. Live embed lag can still produce temporary empty retrieval — see deploy runbook. |

### How to re-verify

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture
# Expect: PASS: 20/20 (or current X/Y) and ret-08 pass
```

---

## EXP-002 — Cost sample: empty-retrieval skip + embed cache (local/sample)

| Field | Value |
|-------|-------|
| Date | 2026-09-13 |
| Environment | local/sample (architecture measurement; Compose API was down during capture — re-run `scripts/sample_cost_latency.py` when stack is up for Langfuse-backed numbers) |
| Baseline | Naïve path: every `/ai/chat` always calls the chat model (completion budget up to `LLM_MAX_TOKENS=2048`) even when retrieval returns no chunks; every re-embed of identical chunk text re-hits the embedding provider. |
| Change | (1) Empty retrieval → **0** generation tokens. (2) Redis embed cache `embed:v1:{sha256(text)}` → cache hit skips provider embed call entirely. (3) Structured surfaces cap completions (`LLM_STRUCTURED_MAX_TOKENS_TAGS=256`, `_METADATA=512`). |
| After | Empty-query generation cost **$0 / 0 tokens** vs up to full completion budget; identical-chunk re-index **0** provider embed calls on cache hit. Fixed query-set procedure: `scripts/sample_cost_latency.py`. |
| Notes | **Not a production SLO.** Fill Langfuse token/cost columns when keys + Compose are available. |

---

## EXP-003 — Agent traces + operator faithfulness (lab)

| Field | Value |
|-------|-------|
| Date | 2026-09-15 |
| Environment | lab (Langfuse Cloud + local Compose; **not** PR CI) |
| Baseline | RAG `rag.answer` traces existed; agent planner/tools were not first-class parents; search-tool RAG opened a sibling root; no documented sampled faithfulness procedure. Fixture harness already **PASS: 20/20**. |
| Change | `agent.turn` parent via `observability.tracing` contextvars; nested `rag.answer` under agent; Prom counters for empty retrieval / HITL / LLM fallback; `POST /ai/feedback`; operator script `evals/run_langfuse_faithfulness.py`. |
| After | Fixture gate still `python evals/run_eval.py --mode fixture`. Operator path: seed dataset + Langfuse UI faithfulness (sampled/nightly). HTTP contracts unchanged. |
| Notes | **Not a production SLO.** Judge scores live in Langfuse, not Prometheus. Do not require this loop to green PRs. |

### How to re-verify

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture
python evals/run_langfuse_faithfulness.py --ui-only
```

---

## EXP-004 — Local RAGAS lab (faithfulness + context precision)

| Field | Value |
|-------|-------|
| Date | 2026-09-16 |
| Environment | lab (operator laptop; **not** VPS, **not** PR CI) |
| Baseline | C-gate fixture **PASS: 20/20** is binary markers only. Langfuse traces exist; RAGAS was documented as optional nightly but had no runnable extra or dedicated judge key. Using `GEMINI_API_KEY` for a judge would share embed/chat-fallback quota. First `--live` attempt crashed on `llm_factory(..., provider=)` under `ragas==0.3.2` (pin forced by `datasets<4`). |
| Change | `evals/run_ragas.py` + `evals/requirements-ragas.txt` bumped to **ragas ≥ 0.4** (+ `instructor[google-genai]`). Judge = `GEMINI_API_KEY_2` only (fail-closed). Default judge model `gemini-3.6-flash`. Collection-failure CLI hint distinguishes API/chat quota from pin failures. Interview pack: `docs/ragas-lab-report.md`. |
| After | **2026-09-16 lab (apply re-run):** seeded retrieval markers; cleared stuck Gemini fallback cache via API restart; `--live --limit 3` → collected **n=3** (ret-01..03); judge=`gemini-3.6-flash` → **faithfulness=1.0000**, **context_precision=NaN** (judge 503/429 mid-batch). Earlier same-day blocked collection: 5/5 chat 500 from Gemini free-tier 429 on chat fallback (empty retrieval still 200). Prior smoke: n=2 with both metrics 1.0000. Not a production SLO. |
| Notes | **Not a production SLO.** Do not add ragas to the API image or CI. Do not copy `GEMINI_API_KEY_2` to the VPS. Chat 500 with hits often = provider quota / fallback cache, not a RAGAS pin bug. Judge NaNs → re-run with `--judge-model` or after quota reset; never invent scores. See `docs/ragas-lab-report.md`. |

### How to re-verify

```powershell
pip install -r evals/requirements-ragas.txt
python evals/run_ragas.py --setup
python evals/run_ragas.py --live --token "<access_token>"
```

---

## EXP-005 — L2 DeepEval GEval (correctness / completeness / style)

| Field | Value |
|-------|-------|
| Date | 2026-09-19 |
| Environment | lab (`http://127.0.0.1`; **not** VPS, **not** PR CI) |
| Baseline | L0 fixture **PASS: 20/20**; L1 live **PASS: 8/8**. Answer quality unmeasured (no `run_quality.py`). 2026-09-18 apply collected `n=1` but GEval means were **NaN** (Gemini judge 503/429; NIM `gpt-oss-20b` timeout). |
| Change | `evals/run_quality.py` + `evals/golden/rag_answers.jsonl` (12 AI-drafted cases) + laptop `requirements-quality.txt`. Judge = `GEMINI_API_KEY_2` (`gemini-3.6-flash`); product answers on NIM Lightning. `--judge-backend nim` hatch for Gemini judge 429/503. |
| After | **2026-09-19 lab:** `--limit 2 --seed-live` → collected **n=2**, SKIP=0, judge=`gemini-3.6-flash` → **correctness=0.75**, **completeness=0.75**, **style=0.10** (exit 0; floor 0.7 met). Per-case: rag-ans-01 1.0/1.0/0.2; rag-ans-02 0.5/0.5/0.0. Style low is an honest generator signal, not omitted. |
| Notes | **Not a production SLO.** Do not add DeepEval to the API image or CI. Style work is a later phase. Re-run without `--limit` when judge quota allows. |

### How to re-verify

```powershell
pip install -r evals/requirements-quality.txt
$env:PYTHONPATH = "src"
python evals/run_quality.py --token "<access_token>" --base-url http://127.0.0.1 --seed-live --environment lab
```

---

## Adding the next experiment

1. Capture baseline `PASS: X/Y` or a named failure mode.
2. Make one change (prompt, threshold, golden, budget).
3. Re-measure; append a new `EXP-00N` section with the template fields.
4. Keep PR CI on fixture goldens only.
