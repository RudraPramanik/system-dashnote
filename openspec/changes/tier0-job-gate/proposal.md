## Why

Blueprint8 Tier 0 (job gate) is the mandatory hire-ready spine—live production proof, stranger FE demo, golden evals, and honest portfolio packaging—but the repo still lacks an `evals/` harness, `goal.md` A–D boxes remain unchecked, and production-live must not be claimed until HTTPS smoke actually passes. Closing Tier 0 unblocks Tier 1 (HITL, Langfuse depth) without breaking the Alive path.

## What Changes

- Prove **A-gate**: hosted data plane + VPS deploy path already scaffolded (7P); record TLS health + `scripts/smoke_prod.py` PASS on the production API URL before any “production-live” claim; sync `goal.md` / runbook gate checklist.
- Enable **B-gate** from this API: ensure prod `CORS_ORIGINS` (and related FE wiring docs) support the sibling `dashnotes` app; track B1–B7 stranger-demo completion in `goal.md` (FE UI work lives in sibling repo; this change owns API/CORS/docs/tracker proof).
- Implement **C-gate** eval harness under `evals/` per `slice8_eval.md` / `ai-eval-harness`: ≥10 golden cases (retrieval + tenant isolation), `run_eval.py` with fixture|live modes, honest pass-rate docs (≥80% target).
- Complete **D-gate** packaging: README live links once proven, eval % + cost/latency fields, demo evidence pointers, interview talk track, GitHub topics as listed in `goal.md`.
- Keep **Alive**: local Compose, chat≠agent, CI without live LLM keys; do not start HITL / GraphRAG / multi-agent.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Add an explicit A-gate / production-live evidence requirement (HTTPS health + smoke PASS recorded) distinct from “7P.8 workflow files exist.”
- `ai-eval-harness`: Add fixture|live runner modes, seed/fixture ID rules, and import-path operator docs needed to ship the missing `evals/` tree for C-gate (without requiring live LLM keys in PR CI).
- `portfolio-baseline`: Require `goal.md` (and README) updates when A/B/C/D evidence lands; forbid premature live/production claims.
- `frontend-developer-guide`: Require API CORS / origin contract for the sibling FE against prod/local, and B-gate tracker completion (B1–B7 + demo path) as a closable gate—not only a guide checklist.

## Impact

- **In this repo (`dashnotesystemv1`)**: new `evals/` tree + runner; possible small CORS/settings/docs/README/`goal.md`/`ship-plan` tracker updates; no intentional API route redesign; chat and agent routes untouched as products.
- **Sibling FE (`dashnotes`)**: B-gate UI/demo/deploy is coordinated outside this OpenSpec apply root; this change documents and tracks proof, and ensures the API accepts the FE origin.
- **Ops**: operator runs against real VPS/hosted services; secrets stay in VPS `.env` / GitHub Secrets only.
- **Out of scope**: Tier 1 HITL (8X.3), Langfuse-native experiments replacing goldens, fixture-eval PR gating as a hard CI job (may document; wire as Tier 1), GraphRAG, multi-agent, Lite Upwork template.
