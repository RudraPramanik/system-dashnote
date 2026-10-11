## Why

Gemini Flash as the default primary burns the free Gemini quota quickly, while NVIDIA NIM typically allows about 40 RPM. Hosted chat should prefer a small, live NIM model for day-to-day speed and quota headroom, with Gemini as the hatch when NIM is rate-limited or gone. The VPS also still needs Langfuse keys and explicit model lines so production traces and the resolved model match what we ship.

## What Changes

- **BREAKING** for operators who relied on Gemini-first defaults: code and example env defaults switch to `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` primary and `gemini/gemini-2.5-flash` as the sole default fallback.
- Keep `gpt-oss-20b`, Super 120B, and Ultra out of the default list (operators may pin them explicitly; local Super pin stays valid).
- Document the NIM-vs-Gemini quota tradeoff and the Lightning-vs-Super speed/quality choice in AI/NVIDIA docs.
- Document the hosted VPS checklist: set Langfuse keys, set the two model lines, recreate `api` and `worker`, confirm `GET /health/ai` and one Langfuse `rag.answer` / `agent.turn` under `environment=production`.
- Ship path: commit the already-implemented tracing fixes with this model flip, then deploy via the existing tag / `workflow_dispatch` CD (not by committing secrets).

Out of scope: using AWS IAM access keys from `infra/tf.env` (those lines are placeholders and must not hold live keys); relocating Postgres/Qdrant; changing the L2 judge model.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `llm-resilience`: Default candidates prefer Lightning NIM, then Gemini Flash. Remove the Gemini-first default requirement introduced by tracing-fix-and-model-update.
- `production-platform`: Hosted VPS env contract includes Langfuse keys and LLM model lines; after those change, `api` and `worker` MUST be recreated so the in-process model cache and tracing client reload.

## Impact

- `src/config.py`, `.env.example`, `.env.production.example`
- `docs/documentation/ai.md`, `docs/nvidia.md`, `docs/deployment/runbook.md` (or observe.md as needed)
- Tests that assert default candidate strings
- Operator VPS `.env` (never committed) and GitHub Actions deploy secrets for SSH
- Uncommitted tracing/Langfuse code from the prior change rides in the same release commit when the operator chooses
