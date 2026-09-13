# EXPERIMENTS — measure → improve

Canonical before/after record for DashNoteSystem quality and cost experiments.
Does **not** replace the golden harness (`evals/run_eval.py`). Fixture CI stays
deterministic; live judges stay operator/nightly.

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

## Adding the next experiment

1. Capture baseline `PASS: X/Y` or a named failure mode.
2. Make one change (prompt, threshold, golden, budget).
3. Re-measure; append a new `EXP-00N` section with the template fields.
4. Keep PR CI on fixture goldens only.
