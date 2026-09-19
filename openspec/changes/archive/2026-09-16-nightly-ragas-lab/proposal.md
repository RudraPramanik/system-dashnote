## Why

Fixture CI and Langfuse traces already exist, but RAGAS faithfulness / context metrics are still only a documented “optional nightly” preference. Operators cannot run a local, off-VPS RAGAS lab with a dedicated judge key, so quality curves stay binary `PASS: X/Y` and the embed/chat Gemini project would be at risk if a judge reused `GEMINI_API_KEY`.

## What Changes

- Add an operator-only RAGAS runner under `evals/` that scores question + answer + retrieved context using a **dedicated** judge key (`GEMINI_API_KEY_2`), never the embeddings / chat-fallback `GEMINI_API_KEY`.
- Document setup + nightly operation (install extra, env, commands, where to record results in `docs/EXPERIMENTS.md`). Label every RAGAS number as **lab**, not a production SLO.
- Keep RAGAS off the VPS, out of Docker Compose API/worker images, out of `.github/workflows/ci.yml`, and off the `/ai/chat` and `/ai/agent` hot path.
- Do **not** add DeepEval, Confident AI, OpenRouter `:free` as the default judge, or Grafana.
- **No BREAKING** HTTP contracts. Fixture `evals/run_eval.py --mode fixture` remains the PR gate.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-eval-harness`: Operator/nightly RAGAS lab becomes a runnable procedure (script + docs + dedicated judge env var). Fixture JSONL CI and Langfuse-native judges stay; RAGAS MUST NOT replace them or run on the VPS.

## Impact

- Eval: new `evals/` operator script + optional `evals/requirements-ragas.txt` (or equivalent extra). `evals/README.md`, `docs/EXPERIMENTS.md`, `docs/documentation/observe.md` / blueprint8 thickener wording.
- Config: placeholder `GEMINI_API_KEY_2=` in `.env.example` only. Do **not** add the key to `src/config.py`, Compose, or VPS `.env`. Operator script reads the env var locally (trim whitespace).
- APIs / tenancy: unchanged. Live answer collection (if used) still uses JWT `wid`; no workspace id from body.
- Dependencies: `ragas` and its extras stay out of the API `requirements.txt` so the VPS image does not grow.
- Soft vs hard: RAGAS remains operator-soft. Postgres/Redis `/health` and fixture evals stay hard gates.
