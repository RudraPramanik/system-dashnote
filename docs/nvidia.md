# NVIDIA NIM — DashNote LLM provider

DashNote uses **LiteLLM** with the `nvidia_nim/` prefix. Base URL: `https://integrate.api.nvidia.com/v1`.

## `.env` (hybrid — recommended)

```env
# LLM → NVIDIA NIM
NVIDIA_NIM_API_KEY=nvapi-...
NVIDIA_NIM_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=nvidia_nim/mistralai/mistral-medium-3.5-128b

# Embeddings → keep Gemini until Qdrant re-index (3072 dim)
GEMINI_API_KEY=...
EMBEDDING_MODEL=gemini/gemini-embedding-2
EMBEDDING_DIMENSION=3072
```

`NVIDIA_API_KEY` is also accepted as an alias for `NVIDIA_NIM_API_KEY`.

## Pre-flight test (run before deploy)

```powershell
python scripts/test_nvidia_nim.py
```

Tests: plain chat, structured JSON (automation tags), tool calling (agent), Gemini embeddings.

## Models evaluated for DashNote

| Model | LiteLLM id | Use |
|-------|------------|-----|
| Mistral Medium 3.5 | `nvidia_nim/mistralai/mistral-medium-3.5-128b` | **Default LLM** — RAG, automation, agent tools |
| DeepSeek V4 Pro | `nvidia_nim/deepseek-ai/deepseek-v4-pro` | Alternative LLM |
| Kimi K2.6 | `nvidia_nim/moonshotai/kimi-k2.6` | Alternative LLM |
| GLM 5.1 | `nvidia_nim/z-ai/glm-5.1` | Alternative LLM |
| Nemotron 3 Ultra | `nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b` | Heavy reasoning (slower) |

Change only `LLM_MODEL` in `.env` to switch — no code change.

## NVIDIA API samples (reference)

See upstream docs at [build.nvidia.com](https://build.nvidia.com/). Raw OpenAI SDK examples use `base_url=https://integrate.api.nvidia.com/v1` and model ids **without** the `nvidia_nim/` prefix; LiteLLM requires the prefix.

## After changing `.env`

```powershell
docker compose up -d --build api worker
```
