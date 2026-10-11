# NVIDIA NIM — DashNote LLM provider

DashNote uses **LiteLLM** with the `nvidia_nim/` prefix. Base URL: `https://integrate.api.nvidia.com/v1`.

Hosted NIM ids are retired without a DashNote code change (HTTP 410). Do **not** pin a single catalog id as the only runtime model. Use `LLM_MODEL` plus `LLM_MODEL_FALLBACKS`. See `docs/documentation/issue_solve.md`.

## `.env` (hybrid — recommended)

```env
# LLM → Lightning NIM primary (~40 RPM), Gemini when NIM is rate-limited
NVIDIA_NIM_API_KEY=nvapi-...
NVIDIA_NIM_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b
LLM_MODEL_FALLBACKS=gemini/gemini-2.5-flash

# Embeddings → keep Gemini until Qdrant re-index (3072 dim)
GEMINI_API_KEY=...
EMBEDDING_MODEL=gemini/gemini-embedding-2
EMBEDDING_DIMENSION=3072
```

`NVIDIA_API_KEY` is also accepted as an alias for `NVIDIA_NIM_API_KEY`.

## Pre-flight test (run before deploy)

```powershell
python scripts/test_nvidia_nim.py --model nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b
```

Tests: plain chat, structured JSON (automation tags), tool calling (agent), Gemini embeddings.

## Models (as of 2026-09-09)

Retired on the hosted integrate API (do not use as sole `LLM_MODEL`):

- `nvidia_nim/mistralai/mistral-medium-3.5-128b` (EOL 2026-08-07)
- `nvidia_nim/z-ai/glm-5.2` (EOL 2026-08-21)
- `nvidia_nim/nvidia/nemotron-3-nano-30b-a3b` (EOL 2026-09-01)
- `nvidia_nim/deepseek-ai/deepseek-v4-pro`, `nvidia_nim/z-ai/glm-5.1`

Pinged working from this stack:

| Model | LiteLLM id | Use |
|-------|------------|-----|
| Nemotron 3.5 Lightning | `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` | **Default primary** — faster small NIM; typical free ~40 RPM |
| Gemini 2.5 Flash | `gemini/gemini-2.5-flash` | Default fallback when NIM is 429/gone/timeout |
| Nemotron 3 Super | `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` | Higher quality, slower; **not** a default hop (operators MAY pin) |
| Nemotron 3 Ultra | `nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b` | Heavy; optional |

A model can appear in `GET /v1/models` and still 404 for this account. Always ping before documenting as default.

**2026-09-23 local restore note:** `openai/gpt-oss-20b` hung (wall-clock); Lightning was flaky; Super 120B + Gemini Flash both pinged PASS. Local `.env` may pin Super **explicitly** as primary with Gemini as distinct fallback — still not a documented default hop. Never set `LLM_MODEL_FALLBACKS` equal to `LLM_MODEL` alone. Full restore steps: `docs/documentation/ai.md` § Operator restore smoke.

## NVIDIA API samples (reference)

See upstream docs at [build.nvidia.com](https://build.nvidia.com/). Raw OpenAI SDK examples use `base_url=https://integrate.api.nvidia.com/v1` and model ids **without** the `nvidia_nim/` prefix; LiteLLM requires the prefix.

## After changing `.env`

Local:

```powershell
docker compose up -d --build api worker
```

Hosted (`aisystem.world`): set `LLM_MODEL`, `LLM_MODEL_FALLBACKS`, and Langfuse keys on the VPS compose `.env` (do not commit that file), then recreate `api` and `worker` so the in-process model cache and Langfuse client reload. See `docs/deployment/runbook.md` §6.1. A restart that keeps the old container env will keep serving the previously cached id. `GET /health/ai` shows `configured_model`, `cached_model`, and `langfuse.enabled` separately. The L2 quality-lab judge stays `gpt-oss-20b`; that id is not a product default.
