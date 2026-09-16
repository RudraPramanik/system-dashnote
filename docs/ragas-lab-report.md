# RAGAS lab report (interview / hire evidence)

**Environment:** lab (operator laptop + local Compose)  
**Not a production SLO.** Not a PR CI gate. Not deployed on the VPS.

This document is the shareable evidence pack for the operator RAGAS lab. Pair it with the deterministic fixture C-gate and the EXPERIMENTS measure→improve record.

---

## Architecture (two layers)

```
┌────────────────────────────────────────────────────────────┐
│  C-gate (hire minimum)                                     │
│  evals/run_eval.py --mode fixture                          │
│  Binary markers / tenant / empty-retrieval / trajectory    │
│  → PR CI friendly, no LLM judge                            │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│  Operator thickener (this lab)                             │
│  evals/run_ragas.py --live                                 │
│  Collect: POST /ai/chat + GET /ai/test-search (JWT wid)    │
│  Score: Faithfulness + ContextPrecision                    │
│  Judge: GEMINI_API_KEY_2 only (never product GEMINI key)   │
│  → laptop / nightly only                                   │
└────────────────────────────────────────────────────────────┘
```

**Eval Paradox framing:** fixture CI stays deterministic; live/operator judges stay sampled and labeled `lab`. See also EXP-001 (empty retrieval) for a stronger measure→improve story than a single perfect score.

---

## Procedure (placeholders only)

```powershell
pip install -r evals/requirements-ragas.txt
python evals/run_ragas.py --setup

# Preflight
# GET http://127.0.0.1/health
# GET http://127.0.0.1/health/ai
# Seed retrieval goldens into the JWT workspace, then:
python evals/run_ragas.py --live --token "<access_token>" --limit 3
```

Do **not** paste live JWTs or API keys into this file or screenshots you share.

---

## Dated results

### Run A — 2026-09-16 (this apply)

| Field | Value |
|-------|-------|
| Date | 2026-09-16 |
| Environment | lab |
| Base URL | `http://127.0.0.1` |
| Cases requested | 3 (`--limit 3`) |
| Collected `n` | **3** (ret-01, ret-02, ret-03) |
| SKIP | 0 on this run |
| Judge model | `gemini-3.6-flash` (`GEMINI_API_KEY_2`) |
| Faithfulness | **1.0000** |
| Context precision | **NaN** (judge jobs hit 503 high-demand / 429 free-tier quota mid-evaluate) |
| Chat model path | Primary NVIDIA NIM after API restart; earlier all-SKIP chat 500s were Gemini fallback **429** with process-cached exhausted model |

**Honest reading:** Collection succeeded after seeding markers and clearing a stuck LLM fallback cache (API restart). Faithfulness scored 1.0 on `n=3`. Context precision is **not** claimed — judge quota produced NaN; do not invent a number.

### Run B — earlier same day (blocked collection)

| Field | Value |
|-------|-------|
| Outcome | **Blocked collection** — 5/5 SKIP `chat 500` |
| Root cause (logs) | `litellm.RateLimitError` / Gemini free-tier quota on `gemini-2.5-flash` (chat fallback). Empty retrieval returned HTTP 200 (no generation); hits path called LLM → 500. |
| Scores | **None** (correct fail-closed behavior) |

### Run C — prior lab smoke (EXP-004 historical)

| Field | Value |
|-------|-------|
| Collected `n` | 2 / 5 (some chat 500 SKIPs) |
| Faithfulness | 1.0000 |
| Context precision | 1.0000 |
| Note | Small-sample smoke only; superseded as the primary narrative by Run A’s larger `n` + honest NaN caveat |

---

## Supporting C-gate

Fixture harness remains the hire minimum. Re-verified during this apply:

```text
PASS: 20/20
```

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture
```


---

## Caveats (say these in interviews)

1. RAGAS scores are **lab** evidence, not SLOs and not merge gates.
2. Always report **`n`**, SKIPs, and NaNs — a lone `1.0` without sample size is weak.
3. Chat HTTP 500 with retrieval hits often means **provider quota / fallback**, not “RAG is broken.”
4. Zero collected rows must never be reported as successful faithfulness.
5. Dedicated judge key (`GEMINI_API_KEY_2`) stays off VPS / Compose API image / product Settings.

---

## Secrets hygiene

- Commands use `<access_token>` only.
- Rotate any JWT previously pasted into a shared terminal history before demos.
- Never commit `.env` keys; never screenshot Langfuse/Google keys into this report.

---

## Related docs

- [`evals/README.md`](../evals/README.md) — how to run fixture + RAGAS
- [`docs/EXPERIMENTS.md`](EXPERIMENTS.md) — EXP-001 … EXP-004
- [`docs/interview-talk-track.md`](interview-talk-track.md) — Eval Paradox / judge talking points
