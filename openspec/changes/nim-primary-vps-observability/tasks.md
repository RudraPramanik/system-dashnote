## 1. NIM-first defaults

- [x] 1.1 Set `LLM_MODEL` and `LLM_MODEL_FALLBACKS` in `config.py`, `.env.example`, and `.env.production.example` to Lightning then Gemini. Keep `gpt-oss-20b` and Super out of those defaults. Do not edit filled `.env` / `.env.production`.
- [x] 1.2 Update `docs/documentation/ai.md` and `docs/nvidia.md` for the NIM-first default, Gemini hatch, and Super-as-explicit-pin note (quota/speed rationale).
- [x] 1.3 Adjust tests that assert the default candidate list (keep intentional Super / `gpt-oss` override tests).

## 2. Hosted AI env contract

- [x] 2.1 Ensure `.env.production.example` documents Langfuse key/host (or base URL) and the two model lines without live secrets.
- [x] 2.2 Add or extend the deploy runbook section: set those vars on the VPS `.env`, recreate `api` and `worker`, confirm `GET /health/ai` and one Langfuse parent under `environment=production`. State that `infra/tf.env` IAM placeholders are not deploy credentials.
- [x] 2.3 Sync delta requirements into main specs when archiving (or via `/opsx-sync` if done earlier).

## 3. Verify and release

- [x] 3.1 Run focused pytest for fallback defaults and health model fields.
- [ ] 3.2 Commit the tracing Langfuse fixes plus this NIM-first flip (no `.env`, no `tf.env` secrets). Push and open/merge PR or land on `production` per repo practice.
- [ ] 3.3 Trigger CD (`workflow_dispatch` or `v*` tag). After deploy, apply VPS env recreate if keys/models were missing, then smoke `GET /health`, `GET /health/ai`, and one hosted chat.
