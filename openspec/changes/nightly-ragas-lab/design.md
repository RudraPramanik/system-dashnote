## Context

See `proposal.md` for why. Today `evals/run_eval.py` is the C-gate (fixture CI `PASS: 20/20`; live search optional). Langfuse traces plus `evals/run_langfuse_faithfulness.py` are the in-product judge path. Blueprint 8 already names RAGAS as optional nightly and forbids DeepEval as a required default. `GEMINI_API_KEY` is the embeddings + chat-fallback project. The operator already has a second local key named `GEMINI_API_KEY_2` (must never be committed). Chat JSON already returns `answer` + `citations` (`POST /ai/chat`), which is enough context text for RAGAS without new API fields.

## Goals / Non-Goals

**Goals:**

- Laptop/nightly RAGAS CLI under `evals/` using `GEMINI_API_KEY_2` as the only judge credential.
- Operator setup + run docs (extra install, env, commands, EXPERIMENTS row).
- Fail closed if `GEMINI_API_KEY_2` is missing; never read `GEMINI_API_KEY` for judging.
- Keep product images, Compose, VPS, and PR CI unchanged.

**Non-Goals:**

- DeepEval, Confident AI, OpenRouter as the default judge, Grafana, recall@k/MRR.
- Scoring `/ai/agent*` trajectories with RAGAS in this change.
- Pushing RAGAS scores into Prometheus or treating them as SLOs.
- Adding `GEMINI_API_KEY_2` to `src/config.py` or shipping RAGAS inside the API image.
- Changing chat vs agent contracts, HITL, or tenant-isolation goldens.

## Decisions

### 1. Operator script in `evals/`, not in `src/` or Compose

Add `evals/run_ragas.py` (name may vary) plus `evals/requirements-ragas.txt`. Install with `pip install -r evals/requirements-ragas.txt` on the operator machine only. Mirror the existing `run_langfuse_faithfulness.py` pattern: `--help` / setup printout, then a real run flag.

**Why:** RAGAS pulls heavy extras (`datasets`, judge SDKs). Putting them in API `requirements.txt` would bloat the VPS image and violate Alive. `evals/` already sits outside `src/` and is not copied into the runtime law for AI modules.

**Alternative considered:** Optional extra in root `pyproject` / `requirements-dev.txt`. Rejected — CI and some local pytest paths might install it accidentally. A dedicated file next to the script is explicit.

**Alternative considered:** Docker service `ragas`. Rejected — user-mandated off VPS; a Compose service would tempt deploy.

### 2. Dedicated env var `GEMINI_API_KEY_2`, never Settings

The script loads dotenv from repo `.env` if present, reads `GEMINI_API_KEY_2`, **strips whitespace**, and uses it only to construct the RAGAS Gemini client (`GOOGLE_API_KEY` / provider factory in-process). It MUST NOT assign `os.environ["GEMINI_API_KEY"]`. Document an empty placeholder in `.env.example` with “local judge / RAGAS only; not embeddings; do not put on VPS.” Leave `.env.production.example` and Compose env files alone.

**Why:** Product Settings are append-only and flow to api/worker. A Settings field would leak the judge key into the running app and invite copying it to the VPS. Fail-closed (no fallback to `GEMINI_API_KEY`) protects embed quota.

**Alternative considered:** Reuse `GEMINI_API_KEY`. Rejected — same Google project as embeddings/chat fallback; judge bursts cause 429s that look like empty retrieval.

**Alternative considered:** OpenRouter `:free`. Rejected as default — 50 req/day is below a 20-case × 2–3 metric run. Operators MAY later point a custom OpenAI-compatible base URL; not in v1 docs as the happy path.

### 3. Default judge model: Gemini Flash on that key

Use a current Flash-class id via RAGAS `llm_factory(..., provider="google")` (id documented in `evals/README.md`, overridable with `--judge-model`). Metrics: **faithfulness** + **context precision** (two metrics to stay inside free RPM/RPD). Skip answer-correctness embeddings unless we can pin them to the judge project without touching the product embedder.

**Why:** Operator already has a second Gemini key; RAGAS documents Gemini; Flash is the free-tier lane. Two metrics ≈ 2×N judge calls.

**Alternative considered:** Also context recall + answer relevancy. Deferred — triples call volume; add later if quota allows.

### 4. Two input modes: setup printout and live-local chat collection

- `--setup` (or `--ui-only` analog): print install + env + commands; no API, no judge.
- `--live`: against **local** default `http://127.0.0.1` with `--token`. For each selected retrieval golden (`query_text`), `POST /ai/chat` with `{ "message": query_text }` only (no workspace fields). Map `answer` + citation/chunk texts into RAGAS `question` / `answer` / `contexts`. Cap with `--limit` (default 5) so a first lab run fits Flash RPM.
- Skip `ret-08` empty-retrieval (no contexts; faithfulness is undefined). Skip tenant and trajectory goldens (different job).

**Why:** Chat already returns grounded answer + citations. `GET /ai/test-search` alone has no generated answer. Defaulting to localhost makes “not VPS” the path of least resistance; `--base-url` may point at a lab API but docs MUST tell operators not to run this on production HTTPS as a merge gate.

**Alternative considered:** Export triples from Langfuse traces. Deferred — extra SDK; live chat is enough for EXP-004.

**Alternative considered:** Fixture-only RAGAS with recorded answers. Weak signal (scores the fixture, not the model). Optional later.

### 5. Docs and EXPERIMENTS, not a fourth dashboard

Update `evals/README.md` (setup + commands + “not CI / not VPS”), `docs/EXPERIMENTS.md` (EXP-00N lab row after a real or honestly skipped first run), `docs/documentation/observe.md` (fourth *lab* plane: RAGAS laptop), `docs/documentation/blueprint8.md` Tier 2 line from “optional RAGAS nightly” to “runnable local lab.” Do not add RAGAS scores to Prometheus.

**Why:** Specs require an EXPERIMENTS record and README procedure. Observe.md already teaches “do not mix planes.”

### 6. Tests stay CI-safe

- Assert `.github/workflows/ci.yml` does not invoke the RAGAS script (extend `tests/observability/test_compat_gate.py` or equivalent).
- Unit-test fail-closed: with `GEMINI_API_KEY` set and `GEMINI_API_KEY_2` empty, the runner refuses (mock, no ragas import required if we isolate credential check).
- Do **not** import `ragas` in pytest CI. Fixture `run_eval.py --mode fixture` still `PASS: 20/20`.

**Why:** CI must not need the extra or the second key.

## Risks / Trade-offs

- [Gemini Flash free RPD/RPM changes] → Mitigation: `--limit` default 5; document “lab not SLO”; operator can rerun later.
- [RAGAS API churn / Gemini factory] → Mitigation: pin a version range in `evals/requirements-ragas.txt`; README names the factory path.
- [Empty retrieval / honest fallback scored as unfaithful] → Mitigation: skip `ret-08`; skip cases with zero citation texts.
- [Operator copies `GEMINI_API_KEY_2` to VPS] → Mitigation: production example + Compose stay silent; README says local only.
- [Whitespace in local `.env` value] → Mitigation: strip on read.
- [Live chat costs product LLM tokens] → Mitigation: small `--limit`; judge key is separate; chat still uses NIM/fallback as today.

## Migration Plan

1. Land script + extra + docs. Operators already holding `GEMINI_API_KEY_2` in local `.env` need no VPS change.
2. Run `--setup`, then `--live` against Compose when the stack is up; paste scores into EXPERIMENTS as `lab`.
3. Rollback: delete `evals/run_ragas.py` and extra; product behavior unchanged. Leave `.env.example` placeholder or revert it.

## Open Questions

None that block specs or tasks. Judge model id can follow whatever Flash lane AI Studio lists at apply time without a spec change.
