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
  fixtures/          # recorded responses for --mode fixture
  run_eval.py        # L0 fixture / L1 live
```

## Runner modes

| Mode | Flag | Behavior |
|------|------|----------|
| **fixture** | `--mode fixture` | Loads recorded JSON under `evals/fixtures/`. No live LLM keys. |
| **live** | `--mode live` | Calls HTTP API (`--base-url` + `--token`). Prefer local Compose or prod. |

PR CI must not require `--mode live` or paid LLM keys. Fixture evals (including
agent trajectory goldens) are wired as a blocking step in `.github/workflows/ci.yml`.

**L0 is keyless.** `python evals/run_eval.py --mode fixture` MUST complete with no
`GEMINI_API_KEY`, `GEMINI_API_KEY_2`, or `NVIDIA_NIM_API_KEY`. It never calls a
live LLM.

**Gemini 429 hatch (later live layers, not L0):** if product chat or live
collection hits Gemini rate-limit / 429, use NVIDIA NIM with a **different free
catalog model** via `LLM_MODEL` / `LLM_MODEL_FALLBACKS` (default extra hop:
`nvidia_nim/openai/gpt-oss-20b` before `gemini/gemini-2.5-flash`) and recreate
`api` + `worker`. Do not wait on Gemini quota to green L0. Do not put an
LLM-as-judge on `/ai/chat` or `/ai/agent`.

## PYTHONPATH / how to run

`evals/` lives outside `src/`. From repo root:

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture

# Live against local nginx edge (docker compose up):
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token "<access_token>"
```

```bash
PYTHONPATH=src python evals/run_eval.py --mode fixture
PYTHONPATH=src python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token "$TOKEN"
```

Exit code `0` only when all selected cases pass. Summary line: `PASS: X/Y`.

### Dual tokens (tenant live)

```powershell
python evals/run_eval.py --mode live --base-url http://127.0.0.1 `
  --token "<owner_or_user_a_jwt>" --token-b "<member_user_b_jwt>"
```

Both JWTs MUST share the same `wid` (workspace). There is no workspace-switch
API yet — prepare membership offline or use fixture mode for isolation cases.

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
| 2026-09-18 | fixture | n/a | **PASS: 20/20** (15 retrieval/tenant + 5 trajectory; no Gemini/NIM keys) |
| 2026-09-07 | fixture | n/a | PASS: 20/20 (15 retrieval/tenant + 5 trajectory) |
| 2026-09-06 | live + `--seed-live` | `http://127.0.0.1` | **PASS: 8/8** (7 skipped: fixture-only / need `--token-b`) |

Target C-gate: ≥80% on the retrieval + tenant set used for hire docs. Record the
honest `PASS: X/Y` even when below 100%.

## Post-C-gate (not replacing this harness)

**Eval lifecycle (canonical map):** [`BLUEPRINT.md`](BLUEPRINT.md) — four layers (fixture CI, live contract, planned DeepEval quality suite, production observability). Fixture `run_eval.py --mode fixture` remains the PR C-gate. The LLM-as-judge quality CLI (`run_quality.py`) is **planned** in that blueprint and is **not** a merge gate.

Langfuse-native datasets/experiments preferred for in-product judges; optional recall@k
and the local RAGAS lab are Tier 2 / nightly. Do not replace this golden CLI.
**PR CI does not run the judge path, RAGAS, or the planned DeepEval quality suite.** None of those are deployed on the VPS.

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
