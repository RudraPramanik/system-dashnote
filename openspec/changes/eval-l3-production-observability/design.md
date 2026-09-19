## Context

See `proposal.md` for motivation. Today:

- L0, L1, and L2 are closed as eval phases. Latest recorded L0 is **PASS: 20/20**. L1 live shares goldens/scorers (`PASS: 8/8` + honest SKIPs). L2 `run_quality.py` exists; low style/correctness on some judge backends is a later generator/threshold concern, not this change.
- L3 serving pieces already exist from `production-ai-observability`: `observability.tracing` (`rag.answer` / `agent.turn`), `POST /ai/feedback`, `dashnote_ai_*` counters, `evals/run_langfuse_faithfulness.py`. That change is not archived into main `ai-feedback`; this change is the **eval-lifecycle close-out**, not a rewrite of those routes.
- Blueprint still labels L3 as an unlabeled “exists” box. There is no L2/L3 alignment section and no apply-time proof that production-shaped keys actually emit traces.
- Settings read `LANGFUSE_HOST` only. Operator `.env.production` already has Langfuse public/secret keys plus `LANGFUSE_BASE_URL`. The client will ignore that host alias until Settings maps it.
- Import law unchanged: Langfuse SDK stays in `langfuse_client.py` / `tracing.py`. AI modules use `observability.tracing` only.

## Goals / Non-Goals

**Goals:**

- Close L3 as the fourth post-blueprint implementation: docs + env alias + apply proof
- Keep L0 aligned with L1 (shared goldens/scorers; re-run fixture; do not fork corpora)
- Place L3 beside L2 (observability, not a replacement GEval)
- Make production-shaped Langfuse env enable the existing lazy client
- Validate traces, feedback, and Prom counters on a real stack using keys the operator already has

**Non-Goals:**

- New golden corpus, DeepEval on the VPS, or GEval/RAGAS on `/ai/chat` or `/ai/agent`
- Thresholds / baseline EXPERIMENTS automation, generator prompt rewrites, `agent_answers.jsonl`
- Making L3 a PR merge gate or requiring Langfuse keys in CI
- Re-implementing tracing, agent trees, or feedback from scratch
- Archiving `production-ai-observability` in this change (optional later)
- Treating traces or thumbs as production SLOs
- Committing or pasting secrets from `.env.production`

## Decisions

### 1. Close-out the existing L3 stack — do not add a second observability path

**Choice:** Keep `observability.tracing`, `POST /ai/feedback`, Prometheus counters, and `run_langfuse_faithfulness.py`. This change gap-fills Settings/docs/eval-lifecycle and proves the path.

**Why:** Serving code already matches the four-layer diagram. A second client or dashboard would drift from `observe.md`.

**Alternative:** New eval-only Langfuse wrapper — rejected; violates “SDK only in observability.”

### 2. L0/L1 alignment = re-validate the shared contract, not new scorers

**Choice:** Alignment stays (a) same `evals/golden/` case ids, (b) same `score_case` / payload normalize, (c) `mode_hint` / `skip_if_modes` eligibility, (d) fixtures as the recorded L1 contract. Apply MUST re-run `--mode fixture` and record a fresh `PASS: X/Y`. Do not add L3 cases to `run_eval.py`.

**Why:** User required L0 stay aligned with L1 while closing L3. Changing goldens for observability would split the C-gate.

**Alternative:** Add Langfuse assertions to `run_eval.py` — rejected; would make L0 need keys and flake CI.

### 3. L2/L3 alignment = placement and tenancy, not shared judges

**Choice:** L3 uses JWT `wid` on traces and feedback (same tenancy as L1/L2). L2 remains the pre-deploy GEval suite. Sampled Langfuse faithfulness stays operator/nightly and off the request path. L3 does not print correctness/completeness floors.

**Why:** Blueprint split: judge scores are lab/pre-deploy; production serving is traces + health + thumbs.

**Alternative:** Await GEval inside chat when Langfuse is on — rejected; hot-path law.

### 4. `LANGFUSE_BASE_URL` is an alias, not a second client

**Choice:** Add `LANGFUSE_BASE_URL` on Settings (default empty). Introduce `effective_langfuse_host`: prefer non-blank `LANGFUSE_HOST`, else `LANGFUSE_BASE_URL`, else `https://cloud.langfuse.com`. `get_langfuse_client()` uses that host. `langfuse_enabled` stays “both keys non-empty.”

**Why:** Production env already uses `LANGFUSE_BASE_URL`. Docs and `.env.example` keep `LANGFUSE_HOST` as the canonical name.

**Alternative:** Tell operators to rename the var only — rejected; apply would still fail on current production-shaped files.

**Apply check:** Unit-test the alias without network. Live proof still uses a real project.

### 5. Validate on an L1-class local (or staging) stack, not “docs say it exists”

**Choice:** Apply uses a reachable API (prefer Compose already proven by L1) with Langfuse keys loaded into the API process (local `.env` or compose env_file). Flow:

1. L0 fixture
2. Optional/recommended L1 live smoke on the same base URL when a JWT exists (NIM hatch if Gemini 429)
3. `POST /ai/chat` (or agent) → capture `thread_id` / optional `trace_id`
4. Confirm a `rag.answer` or `agent.turn` parent in Langfuse UI (flush if the SDK buffers)
5. `POST /ai/feedback` with that JWT + `thread_id` → 2xx
6. `GET /metrics` includes `dashnote_ai_empty_retrieval_total` (and siblings)

Do not require a VPS deploy to close the change. Do not paste keys or JWTs into README.

**Why:** Same honesty gate as L1/L2. Keys already exist; the gap is wiring + proof.

**Alternative:** Unit tests only — rejected; would not prove cloud ingest.

### 6. Feedback contract stays as shipped

**Choice:** No new fields. JWT `wid` authorizes the thread; thumbs or 1–5; optional `trace_id`; 2xx `tracing=unavailable` when Langfuse is off. Chat/agent never call feedback.

**Why:** Spec close-out for `ai-feedback` (missing from main specs). Changing the body would be **BREAKING** for no L3 gain.

**Alternative:** Require `trace_id` — rejected; thread lookup already exists.

### 7. Blueprint roadmap update

**Choice:** Mark L2 done; mark L3 as this phase; keep thresholds / generator / agent answers / nightly judge CI as later separate changes. Add L2/L3 alignment next to the existing L0/L1 and L1/L2 notes.

## Risks / Trade-offs

- **[Risk] Keys set but traces missing because host alias unused** → Mitigation: `effective_langfuse_host`; recreate `api` after env change; record honest miss if cloud ingest still fails.
- **[Risk] SDK buffers traces and UI lags** → Mitigation: flush/shutdown on the known client helper if one exists; wait/retry in apply notes; do not invent a row.
- **[Risk] L3 work accidentally edits goldens and breaks L0/L1** → Mitigation: no golden edits unless a mis-label is found; fixture run is the first apply gate.
- **[Risk] Operator pastes production secrets into chat/docs** → Mitigation: placeholders only; apply reads local env files.
- **[Risk] Scope creep into L2 thresholds or generator prompts** → Mitigation: explicit non-goals; L2 scores stay as already recorded.
- **[Trade-off] L1 live re-run adds time** → Accepted when JWT/stack are available; fixture is the hard L0 alignment proof if live is blocked, and that block must be named.

## Migration Plan

1. Settings alias + client uses `effective_langfuse_host`; CI-safe unit tests
2. BLUEPRINT/README: L3 phase, L0/L1 alignment restated, L2/L3 placement, env var names
3. Confirm CI still fixture-only / no Langfuse
4. Apply: fixture → (live if possible) → chat/feedback/metrics/Langfuse UI
5. Record dated L0 + L3 rows in `evals/README.md` (optional EXPERIMENTS note)
6. Rollback: revert Settings alias and docs; serving routes already shipped stay

## Open Questions

- Whether apply also writes a short EXPERIMENTS row vs README-only — prefer README required; EXPERIMENTS optional if a real trace/feedback proof lands.
- Whether `production-ai-observability` is archived in a later housekeeping change — out of scope here; does not change L3 behavior.
