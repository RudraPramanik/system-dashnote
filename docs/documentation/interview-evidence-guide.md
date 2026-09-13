## Interview evidence — visualize & present

How to **see** cost, evals, messy-data, and the Eval Paradox on a local Compose stack, and what to say in interviews. Companion: [EXPERIMENTS.md](../EXPERIMENTS.md) · [interview-talk-track.md](../interview-talk-track.md) · [observe.md](./observe.md).

**Honesty label:** numbers from this guide are **local/sample** unless you ran them against production HTTPS. Never call them production SLOs.

### What you can show (map)

| Interview question | Where to look | Proof artifact |
|--------------------|---------------|----------------|
| Cost / token optimization | Langfuse `llm_generation` + README cost table | [EXPERIMENTS EXP-002](../EXPERIMENTS.md) · `scripts/sample_cost_latency.py` |
| Eval dataset + reduced error rate | Terminal `PASS: X/Y` + golden JSONL | [EXPERIMENTS EXP-001](../EXPERIMENTS.md) · `evals/` |
| Messy enterprise data | Upload edge file → empty extract → no crash | § Messy-data pipeline above · `tests/shared/fixtures/` |
| Eval Paradox | Talk track + fixture CI vs live | [interview-talk-track.md](../interview-talk-track.md) |

```
                    SHOW IN INTERVIEW
  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐
  │ Terminal    │   │ Langfuse UI  │   │ README /    │
  │ PASS: 20/20 │   │ rag.answer   │   │ EXPERIMENTS │
  └──────┬──────┘   └──────┬───────┘   └──────┬──────┘
         │                 │                   │
         └────────────┬────┴───────────────────┘
                      ▼
              One coherent story
```

---

### 0) Bring the stack up (if migrate/`db` DNS fails)

Symptom: `migrate` exits with `could not translate host name "db"`. Often a stale Postgres container lost the Compose DNS alias `db`.

```powershell
cd g:\projects\notesystem\dashnotesystemv1
docker compose up -d --force-recreate db
docker compose run --rm migrate
docker compose up -d
curl.exe -sS http://127.0.0.1/health
curl.exe -sS http://127.0.0.1/health/ai
```

Expect hard `/health` → `ok`. Soft `/health/ai` may be `ok` or `degraded` (Qdrant/LLM).

Optional UIs while demoing:

| Surface | URL |
|---------|-----|
| API via Nginx | `http://127.0.0.1/` |
| Prometheus | `http://127.0.0.1:9090` |
| Qdrant dashboard | `http://127.0.0.1:6333/dashboard` |
| Langfuse Cloud | `https://cloud.langfuse.com` (needs `LANGFUSE_*` in `.env`) |

---

### 1) Cost monitoring & token optimization (visualize)

**Say (20s):** “We budget context chars and completion tokens by surface, cache embeddings, and skip the LLM entirely on empty retrieval. Traces show tokens/cost per request; here’s a fixed sample and a before/after.”

**Steps:**

1. Confirm Langfuse keys in `.env` (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`). Restart API if you just added them:
   ```powershell
   docker compose up -d api
   ```
2. Register/login → get a JWT (or use an existing token).
3. Run the fixed query set:
   ```powershell
   $env:PYTHONPATH = "src"
   $env:SAMPLE_BASE_URL = "http://127.0.0.1"
   $env:SAMPLE_TOKEN = "<access_token>"
   python scripts/sample_cost_latency.py
   ```
4. Open Langfuse → Traces → **`rag.answer`**:
   - `retrieval` → chunk ids + scores + `latency_ms`
   - `context_building` → `chunks_used`, `char_budget`
   - `llm_generation` → `prompt_tokens`, `completion_tokens`, `cost`, `latency_ms`
5. Force an **empty** query (`completely unrelated zxqv nonsense phrase`) and show: fallback answer, **no** (or skipped) generation spend, optional `empty_retrieval` score.
6. Point at README quality/cost table + [EXPERIMENTS EXP-002](../EXPERIMENTS.md) for the optimization comparison (empty skip + embed cache).

**Screen share order:** terminal sample script → Langfuse one empty + one hit trace → README table.

---

### 2) Evaluation dataset & reduced error rate (visualize)

**Say (25s):** “We keep a golden JSONL corpus for retrieval, tenant isolation, and agent trajectories. Fixture mode gates PRs without paid LLM keys. Here’s the case that encodes empty-retrieval honesty and the before→after in EXPERIMENTS.”

**Steps:**

1. Show goldens (30 seconds in IDE):
   - `evals/golden/retrieval.jsonl` — markers + `ret-08` empty
   - `evals/golden/tenant_isolation.jsonl`
   - `evals/golden/agent_trajectory.jsonl` — forbid surprise `create_note`
2. Run fixture harness (CI-safe):
   ```powershell
   $env:PYTHONPATH = "src"
   python evals/run_eval.py --mode fixture
   # Expect: PASS: 20/20
   ```
3. Optional live (stack + JWT):
   ```powershell
   python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token "<access_token>"
   ```
4. Open [EXPERIMENTS EXP-001](../EXPERIMENTS.md) — baseline failure mode → change → `PASS` including `ret-08`.

**Screen share order:** `PASS: 20/20` terminal → one golden line (`ret-08`) → EXPERIMENTS section → (optional) CI workflow mention.

---

### 3) Messy data shock (visualize)

**Say (20s):** “Bytes land in object storage; a worker extracts text by MIME. Unsupported or corrupt files become empty extract — we don’t invent OCR or poison the vector index with binary garbage.”

**Steps:**

1. Show diagram in this doc (§ Messy-data pipeline).
2. Show fixtures: `tests/shared/fixtures/messy_unsupported.bin`, `messy_empty_pdf.pdf`.
3. Unit proof:
   ```powershell
   python -m pytest tests/shared/test_parsers.py -q
   ```
4. Live path (optional):
   ```powershell
   # Upload a .txt first (happy path), wait ~45s, then check DB / Qdrant
   # Upload binary/unsupported → extracted_text length 0; API/worker stay up
   docker compose logs worker --tail 40
   ```

**Non-claim (say out loud):** No scanned-PDF OCR; no full enterprise ETL — by design for this portfolio slice.

---

### 4) Eval Paradox (visualize / verbal)

**Say (use talk track):** Lab goldens ≠ prod mess; HTTP error rate ≠ answer quality. We keep **fixture CI** for regressions and **live/operator** evals + Langfuse for drift — documented in EXPERIMENTS so we don’t only optimize the golden set.

**Demo combo that sells it:**

1. Prometheus/Grafana-style: HTTP can look fine (`GET /metrics` / `:9090`) while a bad answer is a **quality** failure.
2. Same window: Langfuse empty-retrieval or wrong-chunk retrieval — that is the real signal.
3. Terminal: fixture `PASS: 20/20` (offline gate) vs live run (online check).

Full wording: [interview-talk-track.md § Eval Paradox](../interview-talk-track.md).

---

### 5) Suggested 4-minute interview demo script

| Time | Action | Line |
|------|--------|------|
| 0:00 | Pitch from talk track | Multi-tenant RAG + agent, not a ChatGPT wrapper |
| 0:40 | `run_eval.py --mode fixture` → `PASS: 20/20` | “Regression gate without burning LLM $ on every PR” |
| 1:20 | Langfuse `rag.answer` with citations path | “Retrieval ids/scores + tokens/cost on one request” |
| 2:10 | Empty query → honest fallback | “Cost + quality: 0 gen tokens, no hallucination” |
| 2:40 | EXPERIMENTS.md EXP-001 / EXP-002 | “We measured, changed, re-measured” |
| 3:10 | Messy fixture / pipeline diagram | “Enterprise mess: fail extract safely” |
| 3:40 | Eval Paradox one-liner | “Fixture ≠ live; HTTP OK ≠ good answer” |

Keep a browser tab set: Langfuse · Prometheus · this doc · EXPERIMENTS · README metrics table.
