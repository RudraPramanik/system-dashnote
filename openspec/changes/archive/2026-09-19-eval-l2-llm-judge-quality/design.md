## Context

See `proposal.md` for motivation. Today:

- L0 and L1 are closed: fixture CI **PASS: 20/20**, live contract with shared goldens/scorers, NIM hatch documented for product Gemini 429.
- L2 is blueprint-planned only: no `run_quality.py`, no `rag_answers.jsonl`, no `requirements-quality.txt`.
- Closest existing judge path is the RAGAS lab (`evals/run_ragas.py` + `GEMINI_API_KEY_2`) — keep it; do not delete or fold it in this change.
- Product LLM walk on 429 → next `LLM_MODEL_FALLBACKS` (NIM before Gemini Flash) already ships; L2 collection **consumes** that hatch the same way L1 does.
- Blueprint forbids importing DeepEval from `run_eval.py` and forbids putting the judge on the hot path.

## Goals / Non-Goals

**Goals:**

- Ship L2 phase-1: RAG answer goldens + DeepEval GEval quality CLI + laptop requirements + docs + L1/L2 alignment
- Fail-closed judge key / empty-n / NaN behavior matching the blueprint
- Apply validation: real run recorded (or honest fail-closed), NIM hatch if product 429 blocks collection

**Non-Goals:**

- `agent_answers.jsonl`, threshold/baseline EXPERIMENTS automation, generator prompt rewrites
- Making L2 a PR merge gate or adding DeepEval to API/worker images
- Replacing or deleting RAGAS / Langfuse labs
- Changing product tenancy or merging chat/agent
- Using product `GEMINI_API_KEY` as the judge
- Default Super 120B / Ultra 550B hops

## Decisions

### 1. Separate quality CLI — do not extend `run_eval.py`

**Choice:** New `evals/run_quality.py` (+ optional small helpers under `evals/` if needed). C-gate stays `run_eval.py` only.

**Why:** Blueprint: one quality runner; do not import DeepEval from the C-gate. Keeps PR CI free of judge deps.

**Alternative:** Flags on `run_eval.py` — rejected; mixes layers and CI surface.

### 2. L1/L2 alignment = shared live stack contract, not shared scorers

**Choice:** Alignment means (a) same JWT `wid` tenancy on live calls, (b) same seed / marker ID law and reuse of retrieval golden note content where possible, (c) same Compose/staging target + NIM hatch for product 429, (d) README/BLUEPRINT stating L2 sits on a proven L1-class stack. L2 does **not** reuse marker PASS/FAIL scoring; it uses GEval against answer goldens.

**Why:** L0/L1 prove retrieval/tenant contract; L2 measures answer quality. Sharing scorers would blur layers.

**Alternative:** Score markers inside `run_quality.py` — rejected; duplicates L1.

### 3. Collection surface is `POST /ai/chat` only

**Choice:** Phase-1 goldens and collection call chat with `message` (plus existing product fields). Do not collect via `/ai/agent`.

**Why:** Blueprint RAG-first; trajectories stay L0/L1.

**Alternative:** Agent-only for richer tools — rejected for this phase.

### 4. DeepEval GEval with Gemini judge key; product NIM for generator 429

**Choice:** Judge = DeepEval `GEval` via dedicated `GEMINI_API_KEY_2` and `--judge-model` (default from blueprint, e.g. `gemini-3.6-flash` or the nearest available pin documented at apply time). Product answer generation stays on `LLM_MODEL` / `LLM_MODEL_FALLBACKS`. On product Gemini 429, operators switch to a **different free/catalog NIM model**, recreate `api` + `worker`, re-collect — same as L1. Judge 429/503 → re-run / lower concurrency / different `--judge-model`; do **not** silently use product key or invent scores. Do not implement a second judge provider walk inside the quality CLI in this change unless apply proves Gemini judge is unusable and a documented DeepEval-compatible alternative is required — prefer re-run and NIM for **product** collection first.

**Why:** Blueprint separates judge key from product key; NIM hatch is for live product paths, not for stuffing a judge onto `/ai/chat`.

**Alternative:** Point DeepEval judge at NIM in v1 — deferred unless apply is blocked; document as follow-up if needed.

### 5. Goldens: ~10–20 AI-drafted, seed-aligned with retrieval markers

**Choice:** Author `rag_answers.jsonl` with checklist + expected prose; seed from or mirror retrieval marker notes so L1 `--seed-live`-class content works for chat. Label corpus AI-drafted/curated in README.

**Why:** Blueprint seed law + teacher-bias honesty; small set keeps apply runnable.

**Alternative:** Hundreds of cases — rejected for phase 1.

### 6. Hard floors for correctness/completeness; style report-only

**Choice:** Default floors ≈ 0.7 for correctness and completeness (CLI flags or constants, tunable later). Style always printed; no hard floor (or a very loose one) in v1.

**Why:** Matches blueprint; low style is an honest generator signal for a later phase.

### 7. Apply is not done until quality run is validated

**Choice:** Final tasks MUST:

1. Confirm L0 still green: `python evals/run_eval.py --mode fixture`
2. Prefer L1 still healthy on the same stack (optional but recommended smoke)
3. `pip install -r evals/requirements-quality.txt`; set `GEMINI_API_KEY_2`
4. Bring up Compose (or staging), JWT, seed answer notes if needed
5. Run `python evals/run_quality.py --token … --base-url …`
6. On product Gemini 429, NIM hatch + recreate + re-run
7. Record aggregates / `n` / SKIPs / judge model / env in `evals/README.md`

Exit non-zero on fail-closed or hard-floor miss. Zero scored rows fails the apply gate.

**Alternative:** Docs-only L2 — rejected; user required validation.

### 8. Blueprint roadmap update

**Choice:** Mark L1 done; mark L2 as this phase; keep thresholds / agent answers / nightly workflow as later separate changes.

## Risks / Trade-offs

- **[Risk] Product Gemini 429 empties collection** → Mitigation: NIM different free model + recreate api/worker; SKIP honesty; never fabricate means.
- **[Risk] Judge Gemini 429 / DeepEval flake** → Mitigation: `--limit`, re-run, `--judge-model` override; fail closed; do not use product key.
- **[Risk] Teacher bias (same family gold + generator)** → Mitigation: checklist-heavy goldens; label AI-drafted; human spot-check note in docs.
- **[Risk] Empty retrieval SKIPs dominate** → Mitigation: seed notes with wait_embed; reuse L1 seed content; apply fails if `n=0`.
- **[Risk] Scope creep into agent/thresholds** → Mitigation: explicit non-goals; no `agent_answers.jsonl` this change.
- **[Trade-off] Style may score low** → Accepted; report it; generator work is a later phase.

## Migration Plan

1. Docs + blueprint roadmap + README L2 / L1 alignment / NIM hatch
2. Add `rag_answers.jsonl`, `requirements-quality.txt`, `run_quality.py`
3. CI-safe unit tests for fail-closed helpers only (no live HTTP / no paid judge in pytest)
4. Operator validation: fixture → quality run; NIM if needed
5. Record README (optional EXPERIMENTS row); leave CI fixture-only
6. Rollback: remove quality files/docs; product NIM fallbacks already shipped stay

## Open Questions

- Exact default `--judge-model` string pin if `gemini-3.6-flash` is unavailable at apply time — resolve during apply against current DeepEval/Gemini catalog; document the pin used.
- Whether a single dated EXPERIMENTS row is written in this change vs README-only — prefer README required; EXPERIMENTS optional if a real scored run lands.
