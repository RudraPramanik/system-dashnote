# Eval harness (Tier 0 / C-gate)

Golden corpus + CLI for retrieval quality and tenant isolation. Aligns with
`docs/documentation/blueprint/slice8_eval.md` and `openspec/specs/ai-eval-harness`.

## Layout

```
evals/
  BLUEPRINT.md                 # eval lifecycle map (L0–L3)
  README.md
  golden/
    retrieval.jsonl
    tenant_isolation.jsonl
    agent_trajectory.jsonl
    rag_answers.jsonl          # L2 answer goldens (AI-drafted/curated)
  fixtures/          # recorded responses for --mode fixture
  run_eval.py        # L0 fixture / L1 live
  run_quality.py     # L2 DeepEval GEval (laptop / pre-deploy)
  requirements-quality.txt
```

## Runner modes

| Mode | Flag / command | Behavior |
|------|----------------|----------|
| **L0 fixture** | `run_eval.py --mode fixture` | Loads recorded JSON under `evals/fixtures/`. No live LLM keys. **PR CI.** |
| **L1 live** | `run_eval.py --mode live` | Calls HTTP API (`--base-url` + `--token`). Same goldens + scorers as L0. Operator / nightly — **not** a merge gate. |
| **L2 quality** | `run_quality.py` | Collects `POST /ai/chat` answers from `rag_answers.jsonl`, scores with DeepEval GEval. Local / pre-deploy — **not** a merge gate. |
| **L3 observability** | Langfuse UI + `POST /ai/feedback` + `GET /metrics` | Serving traces, thumbs, and low-cardinality quality counters. **Not** a merge gate. **Not** a production SLO. |

**L0/L1 alignment.** One corpus under `evals/golden/`, one scorer in `run_eval.py`. Fixtures are the recorded L1 contract for CI. Live proves eligible cases (`mode_hint` `either` / `live`) against Compose or staging. Fixture-only cases and live trajectories SKIP with an explicit reason — they are not a second golden set. L3 does **not** replace this contract.

**L1/L2 alignment.** L2 uses the same JWT `wid` tenancy, seed/marker ID law (answer seeds reuse retrieval-marker note content), and Compose/staging target class as L1. Prefer a stack already proven by L1. L2 does **not** replace marker PASS/FAIL scoring — it adds answer-quality GEval.

**L2/L3 alignment.** L3 traces and `POST /ai/feedback` use the same JWT `wid` as L1/L2. L2 GEval stays local/pre-deploy and off `/ai/chat` and `/ai/agent`. Traces and thumbs do **not** replace L0/L1 `PASS: X/Y` or L2 aggregates.

PR CI must not require `--mode live`, `run_quality.py`, Langfuse keys, or paid LLM keys. Fixture evals (including
agent trajectory goldens) are wired as a blocking step in `.github/workflows/ci.yml`.

**L0 is keyless.** `python evals/run_eval.py --mode fixture` MUST complete with no
`GEMINI_API_KEY`, `GEMINI_API_KEY_2`, or `NVIDIA_NIM_API_KEY`. It never calls a
live LLM.

**Gemini 429 hatch (L1 / L2 product live stack, not L0):** if live seed/embed, product
chat, or L2 collection hits Gemini rate-limit / 429, use NVIDIA NIM with a
**different free catalog model** via `LLM_MODEL` / `LLM_MODEL_FALLBACKS` (default
extra hop: `nvidia_nim/openai/gpt-oss-20b` before `gemini/gemini-2.5-flash`) and
recreate `api` + `worker`. Do not wait on Gemini quota to green L0 or to close L1/L2.
Do not put an LLM-as-judge on `/ai/chat` or `/ai/agent`. The eval CLI does not
switch models itself — configure the product stack, then re-run.

## PYTHONPATH / how to run

`evals/` lives outside `src/`. From repo root:

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture

# L1 live against local nginx edge (docker compose up):
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode live --base-url http://127.0.0.1 `
  --token "<access_token>" --seed-live
```

```bash
PYTHONPATH=src python evals/run_eval.py --mode fixture
PYTHONPATH=src python evals/run_eval.py --mode live --base-url http://127.0.0.1 \
  --token "$TOKEN" --seed-live
```

**L1 preflight:** `GET /health` and `GET /health/ai` ok; JWT valid for the eval
workspace; prefer `--seed-live` so marker notes exist before search. Record runs as
environment `live-local` (or staging). Exit `0` only when every **scored** case
passes. Summary: `PASS: X/Y` plus `SKIP: N` with reasons. Live with **zero scored
cases** (all SKIP) exits non-zero — that is not a successful L1 close-out.

### Dual tokens (tenant live)

```powershell
python evals/run_eval.py --mode live --base-url http://127.0.0.1 `
  --token "<owner_or_user_a_jwt>" --token-b "<member_user_b_jwt>" --seed-live
```

Both JWTs MUST share the same `wid` (workspace). There is no workspace-switch
API yet — prepare membership offline or use fixture mode for isolation cases.
Cases with `actor=b` **SKIP** (never PASS) when `--token-b` is missing — the
runner MUST NOT treat `--token` as the member.

## L2 quality (DeepEval GEval)

Frozen RAG answer goldens + laptop judge. Corpus is **AI-drafted, then curated**
(`evals/golden/rag_answers.jsonl`) — not expert-labeled from day one. Trajectory
goldens stay L0/L1; they are not the L2 answer suite.

```powershell
pip install -r evals/requirements-quality.txt
$env:PYTHONPATH = "src"
python evals/run_quality.py --setup
python evals/run_quality.py --token "<access_token>" --base-url http://127.0.0.1 --seed-live --environment lab
```

Default judge is NVIDIA NIM `gpt-oss-20b` (different catalog id from product Lightning). Same `NVIDIA_NIM_API_KEY`. Smoke path: add `--limit 2`. Do **not** paste `>>` comment lines into PowerShell. Do **not** put a real JWT in this README.

Opt-in Gemini judge (when `GEMINI_API_KEY_2` quota exists):

```powershell
python evals/run_quality.py --token "<access_token>" --base-url http://127.0.0.1 --seed-live --judge-backend gemini --judge-model gemini-3.6-flash
```

**Requires** `NVIDIA_NIM_API_KEY` for the default NIM judge. `--judge-backend gemini` requires `GEMINI_API_KEY_2`. Never falls back to product `GEMINI_API_KEY`. Install DeepEval on the laptop only — not in the API image.

**Judge scale.** DeepEval GEval asks for an integer from 0 to 10 and divides by 10 before the 0.7 floors. Evaluation steps must not tell the judge to score from 0 to 1. That instruction collapsed an earlier lab paste (`evals/eval_report.md`) onto `0.00` / `0.05` / `0.10`. Do not cite that paste as a later run’s result.

**Durable record.** Each scored run replaces `evals/quality_scores.jsonl` (case id, scores, and reasons, including when the score is numeric) and writes `evals/eval_report_2.md` from that file. The console can be overwritten by DeepEval’s progress bar; the JSONL is the source of truth.

**Style voice.** Style scores the answer string only: concise, no invented facts, marker tokens preserved, and the product refusal sentence when context is thin (`I could not find relevant information in your notes and files for this query.`). Do not require citation prose inside the answer. Citations stay a sibling field. Generator-prompt edits and agent-answer goldens stay later work.

**Honesty fields:** environment (`lab` / `pre-deploy`), judge model, per-metric
aggregates (correctness, completeness, style), collected `n`, SKIP count/reasons,
NaN notes. Correctness + completeness hard floor default **0.7**; style is always
reported (loose / no floor). Exit non-zero on missing judge key, `n=0`, all-NaN
required metrics, or hard-floor miss — never invent scores. A floor miss still leaves the JSONL and `eval_report_2.md`.

**Collection SKIPs:** non-200, empty answer, empty retrieval, HTTP timeout, or
other request-transport failure. A timed-out `POST /ai/chat` is SKIP (remaining
cases still run), not an uncaught traceback. A full-set run with only timeout
SKIPs is fail-closed (`n=0`), not a successful L2 close-out. `--limit` is the
smoke path. Uncaught `httpx.ReadTimeout` is a harness bug.

**Preflight:** same as L1 (`/health`, `/health/ai`, JWT). Prefer `--seed-live`.
Product chat stays on NIM Lightning. Judge default is a different NIM id
(`gpt-oss-20b`). Gemini judge is opt-in. Do not use the product Gemini key.
Mint a fresh access token; do not paste JWTs into docs or chat.

## L3 observability (Langfuse + feedback + Prom)

Production-serving traces and health. Prefer a stack already proven by L1. Chat and agent **never** await a judge. L3 is **not** a PR merge gate and **not** a production SLO.

**Enable (API process env — placeholders only):**

| Var | Role |
|-----|------|
| `LANGFUSE_PUBLIC_KEY` | Project public key (`pk-lf-…`) |
| `LANGFUSE_SECRET_KEY` | Project secret key (`sk-lf-…`) |
| `LANGFUSE_HOST` | Canonical host (EU `https://cloud.langfuse.com`; US `https://us.cloud.langfuse.com`) |
| `LANGFUSE_BASE_URL` | Alias used when `LANGFUSE_HOST` is blank (production-shaped env) |

Both keys must be non-empty. Recreate `api` after env changes. Soft: missing keys do not fail `/health` or `/ai/chat`. Do **not** paste live keys or JWTs here.

**Prove a turn (Compose / staging):**

1. `GET /health` and `GET /health/ai` ok. JWT for the eval workspace.
2. `POST /ai/chat` with `{"message": "<query>"}` (message only; `wid` from token). Capture `thread_id` (and optional `trace_id`).
3. Langfuse UI: parent **`rag.answer`** (chat) or **`agent.turn`** (agent). Flush/wait if the SDK buffers.
4. `POST /ai/feedback` with JWT + `thread_id` + `thumbs` (`up`/`down`) or `score` (1–5). Expect 2xx. When Langfuse is off: 2xx `tracing=unavailable`.
5. `GET /metrics` still includes `dashnote_ai_empty_retrieval_total`, `dashnote_ai_agent_interrupt_total`, `dashnote_ai_llm_fallback_total` (no per-user judge labels).

```powershell
# After a chat turn — placeholders only
curl.exe -sS -X POST http://127.0.0.1/ai/feedback `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d "{\"thread_id\": \"<thread_uuid>\", \"thumbs\": \"up\"}"
```

Sampled faithfulness stays `evals/run_langfuse_faithfulness.py` (operator/nightly). Do **not** add it to CI.

## Golden schema

Common fields:

| Field | Meaning |
|-------|---------|
| `id` | Stable case id |
| `theme` | `retrieval` \| `tenant_isolation` \| `agent_trajectory` |
| `mode_hint` | `fixture` \| `live` \| `either` |
| `surface` | e.g. `GET /ai/test-search` or `POST /ai/agent` |
| `skip_if_modes` | optional list of modes to skip |

**Retrieval** extras:

- `query_text`
- `expect_content_markers` — substrings that should appear in hit text (preferred over hard-coded UUIDs)
- `expect_min_hits` — optional int
- `fixture_ref` — filename under `evals/fixtures/` for fixture mode
- `seed` — optional live seed: `{ "title", "content", "is_private", "wait_embed_sec" }`

**Tenant isolation** extras:

- `actor` — which token: `a` \| `b` (default `b` for deny cases)
- `expect_no_content_markers` — markers that must **not** appear for the actor
- `fixture_ref` — recorded search response for fixture mode
- `forged_workspace_probe` — if true, live mode sends an extra body field; results must still be JWT-scoped (Pydantic ignores unknown fields; workspace never taken from body)

**Agent trajectories** (Tier 1):

- `forbidden_tools`, `required_tools`, `sequence_mode` (`exact` \| `subset`)
- `fixture_ref` — JSON with `{ "tools": [...], "answer": "..." }` (no live LLM in fixture mode)
- At least one case must forbid surprise `create_note`
- Live trajectory scoring is not required for CI (fixture-only)

## Seed / fixture ID law

- Do **not** hard-code `note_id` / `chunk_id` that only exist in one environment.
- Prefer `expect_content_markers` + live `seed`, or `fixture_ref` recorded hits.
- Document any seed script steps here when added.

## Latest recorded run

| When | Mode | Target | Result |
|------|------|--------|--------|
| 2026-09-23 | L2 `run_quality.py` `--seed-live` (full 12) | `http://127.0.0.1` (`lab`) | **exit 0.** Judge `nvidia_nim/openai/gpt-oss-20b`. n=12 · SKIP=0 · correctness=0.9000 · completeness=0.7417 · style=1.0000 · floor 0.7 met. Record is `evals/quality_scores.jsonl` and `evals/eval_report_2.md`. Narrative: `evals/article.md`. The earlier `evals/eval_report.md` paste (means near 0.08) is the 0–1 scale artifact, not this result. Generator prompt was not changed. Not a production SLO. |
| 2026-09-19 | L3 traces + `POST /ai/feedback` + `/metrics` | `http://127.0.0.1` (`lab`) | **Proven.** Chat returned `thread_id` + `trace_id` (`chunks_retrieved=7`). Langfuse list showed parent **`rag.answer`**. Feedback HTTP 200 `tracing=recorded`. `/metrics` includes `dashnote_ai_empty_retrieval_total`, `dashnote_ai_agent_interrupt_total`, `dashnote_ai_llm_fallback_total` (no per-user judge labels). Langfuse SDK v3: scores via `create_score`. Product chat used NIM hatch `nvidia_nim/openai/gpt-oss-20b` after Lightning resolve/timeout. **Not a production SLO.** Not a merge gate. |
| 2026-09-19 | live + `--seed-live` | `http://127.0.0.1` (`live-local`) | **PASS: 8/8** (SKIP: 12 — 11 fixture-only / L0 recorded form; 1 `actor=b` needs `--token-b`). Same `evals/golden/` corpus and scorers as L0. L0/L1 alignment re-check during L3 apply. |
| 2026-09-19 | fixture | n/a | **PASS: 20/20** — L0 alignment check during L3 apply (15 retrieval/tenant + 5 trajectory; no Langfuse/judge keys) |
| 2026-09-19 | L2 `run_quality.py` `--limit 2 --seed-live` NIM judge | `http://127.0.0.1` (`lab`) | **exit 1** (hard floors missed, not a hang). Product chat = NIM Lightning. Judge = `nvidia_nim/openai/gpt-oss-20b` (`--judge-backend nim`). n=2 · SKIP=0 · correctness=0.075 · completeness=0.050 · style=0.075. Per-case: rag-ans-01 0.1/0.0/0.1; rag-ans-02 0.05/0.1/0.05. ~5 min. Numeric scores (not NaN). Not a production SLO. |
| 2026-09-19 | L2 `run_quality.py` `--seed-live` (full 12, timeout 300s) | `http://127.0.0.1` (`lab`) | **collection crash gone** — no uncaught `httpx.ReadTimeout`. Collected n=9 · SKIP=3 (`rag-ans-10` empty retrieval; `rag-ans-11`/`rag-ans-12` chat HTTP 401). Remaining cases still ran after SKIPs. Judge=`gemini-3.6-flash`: rag-ans-01 1.0/1.0/0.4; then **429 RESOURCE_EXHAUSTED** (NaNs on later GEval). Process ended mid-judge before aggregates. Fail-closed / incomplete GEval — not a scored close-out. Product stack NIM Lightning. Not a production SLO. |
| 2026-09-19 | L2 `run_quality.py` `--limit 2 --seed-live` | `http://127.0.0.1` (`lab`) | **exit 0** · judge=`gemini-3.6-flash` · n=2 · SKIP=0 · correctness=0.75 · completeness=0.75 · style=0.10 · floor 0.7 met. Per-case: rag-ans-01 1.0/1.0/0.2; rag-ans-02 0.5/0.5/0.0. Product stack NIM Lightning. Not a production SLO. |
| 2026-09-18 | L2 `run_quality.py` `--limit 1 --seed-live --judge-backend nim` | `http://127.0.0.1` (`lab`) | **fail-closed** (exit 2): collected `n=1` (`rag-ans-01-alpha-milestone`), SKIP=0; correctness/completeness/style **NaN** — NIM `gpt-oss-20b` judge timed out. Product collection used NIM Lightning. Gemini judge earlier hit 503/429. Not a successful GEval close-out; do not invent scores. |
| 2026-09-18 | fixture | n/a | **PASS: 20/20** — L0 alignment check during L2 apply |
| 2026-09-18 | live + `--seed-live` | `http://127.0.0.1` (`live-local`) | **PASS: 8/8** (12 SKIP: 11 fixture-only / L0 recorded form; 1 `actor=b` needs `--token-b`). Stack LLM already NIM Lightning; no Gemini 429. |
| 2026-09-18 | fixture | n/a | **PASS: 20/20** (15 retrieval/tenant + 5 trajectory; no Gemini/NIM keys) — L0 alignment check during L1 apply |
| 2026-09-07 | fixture | n/a | PASS: 20/20 (15 retrieval/tenant + 5 trajectory) |
| 2026-09-06 | live + `--seed-live` | `http://127.0.0.1` | PASS: 8/8 (7 skipped: fixture-only / need `--token-b`) — historical; superseded by 2026-09-18 live row |

Target C-gate: ≥80% on the retrieval + tenant set used for hire docs. Record the
honest `PASS: X/Y` even when below 100%.

## Post-C-gate (not replacing this harness)

**Eval lifecycle (canonical map):** [`BLUEPRINT.md`](BLUEPRINT.md) — four layers (L0 fixture CI, L1 live contract, L2 DeepEval quality suite, L3 production observability). Fixture `run_eval.py --mode fixture` remains the PR C-gate. L1 live is operator/nightly. L2 `run_quality.py` is local/pre-deploy and is **not** a merge gate. L3 traces/feedback/Prom are serving observability and are **not** a merge gate.

Langfuse-native datasets/experiments preferred for in-product judges; optional recall@k
and the local RAGAS lab are Tier 2 / nightly. Do not replace this golden CLI.
**PR CI does not run the judge path, RAGAS, or the DeepEval quality suite.** None of those are deployed on the VPS.

### Operator / nightly faithfulness judge

Off the `/ai/chat` and `/ai/agent` hot path. Chat/agent never await a judge.

```powershell
$env:PYTHONPATH = "src"
python evals/run_langfuse_faithfulness.py --ui-only
# With Langfuse keys set:
python evals/run_langfuse_faithfulness.py --seed-dataset
```

The script seeds (or documents) dataset `dashnote-retrieval-goldens` from
`evals/golden/retrieval.jsonl` and prints Langfuse UI steps for a sampled
faithfulness evaluator (5–10% or nightly batch). Do **not** add it to
`.github/workflows/ci.yml`.

### Operator / nightly RAGAS lab (laptop)

Scores question + answer + retrieved context with a **dedicated** judge key
(`GEMINI_API_KEY_2`). Never uses `GEMINI_API_KEY` (embeddings / chat fallback).
Install the extra on the laptop only — not in `requirements/base.txt` / the API image.
Requires **ragas ≥ 0.4** (`llm_factory(..., provider="google", client=...)`)
and `instructor[google-genai]` (jsonref for Gemini structured output).
Default `--judge-model` is `gemini-3.6-flash` (override if your AI Studio project
lists a different Flash id). If you previously installed an older pin, reinstall:

```powershell
pip install -r evals/requirements-ragas.txt
python evals/run_ragas.py --setup
# Local Compose + JWT (default http://127.0.0.1, --limit 5):
python evals/run_ragas.py --live --token "<access_token>"
```

**Live preflight (collection ≠ judge):**

1. `GET /health` and `GET /health/ai` ok.
2. JWT valid for a workspace that already has seeded retrieval notes (marker goldens), or seed them first.
3. Spot-check `POST /ai/chat` for a golden query — expect HTTP 200 with `chunks_retrieved > 0`.
4. If every case SKIPs with chat HTTP 500, read API logs: often Gemini free-tier **429** on the chat fallback model, or a stuck in-process LLM fallback cache (restart API after quota clears). That is **not** a `requirements-ragas.txt` pin failure.
5. Zero collected rows → CLI exits non-zero with a collection-failure hint (no fabricated scores).
6. Judge 429/503 can yield `NaN` for a metric even when collection succeeded — re-run with `--judge-model` or after quota reset; do not invent scores.

`--setup` prints the checklist with no network. `--live` calls `POST /ai/chat`
(`message` only) and `GET /ai/test-search` (`q` only) — workspace stays on the JWT.
Skips `ret-08` / empty retrieval, tenant, and trajectory goldens. Record scores in
EXPERIMENTS as **lab**, not a production SLO. Do **not** add this to CI or the VPS.

**Interview / hire evidence pack:** [`docs/ragas-lab-report.md`](../docs/ragas-lab-report.md)

**Before/after record:** [`docs/EXPERIMENTS.md`](../docs/EXPERIMENTS.md) — measure→improve
loops tied to this harness (e.g. empty-retrieval / `ret-08`) and lab judge/RAGAS loops.
