## Context

See proposal.md for why. Code defaults today are Gemini Flash → Lightning (from the just-archived tracing change). Local `.env` already pins Super 120B with Gemini fallback. Hosted `GET /health/ai` previously stuck on `gpt-oss-20b`. Langfuse tracing labels and closed roots are already implemented in the working tree but not yet released. `infra/tf.env` lists the EC2 identity and explicitly placeholders IAM keys — deploy uses GitHub Actions SSH (`VPS_*` secrets), not those IAM lines.

## Goals / Non-Goals

**Goals:**

- Prefer Lightning NIM for routine product chat (~40 RPM headroom vs Gemini free).
- Keep Gemini as the single default hatch.
- Make the VPS env + recreate steps unambiguous so Langfuse and the model list actually load in production.
- Release path: one commit (tracing + NIM flip), CI on PR, CD via `workflow_dispatch` or `v*` tag.

**Non-Goals:**

- Making Super 120B the documented default (slower; operators may pin it, as local already does).
- Putting live Langfuse or AWS keys in git.
- Using placeholder IAM keys from `tf.env` for SSH or AWS API calls.
- Changing the L2 quality-lab judge (`gpt-oss-20b` may remain the judge).

## Decisions

### 1. Lightning primary, Gemini fallback

Lightning is the small/fast NIM id already pinged in this stack. Super is better for some answers but slower and was intentionally kept off the default hop. Gemini remains the hatch when NIM returns 429/410/timeout. `gpt-oss-20b` stays out of defaults (hang risk).

Alternative considered: Super as default. Rejected for product defaults because the user asked for faster responses; Super remains an explicit pin documented in `docs/nvidia.md`.

### 2. VPS apply is operator + CD, not committed secrets

Langfuse keys from the laptop `.env` and model lines go onto the VPS compose `.env` via SSH or an existing operator process. CD (`deploy.yml`) rebuilds/pulls the image and runs migrate/up/health/smoke. Recreate `api`/`worker` after env edits. Never copy filled `.env` into the repo or into `tf.env`.

### 3. Release includes uncommitted tracing work

The working tree already has the Langfuse naming/TTFT/health work. This change’s apply flips the model defaults and docs; the release commit should include both so production gets measurable traces and the NIM-first list together.

## Risks / Trade-offs

- [Lightning flaky or 410 for this entitlement] → Fallback to Gemini; operator may pin Super explicitly after a ping.
- [NIM 40 RPM still exhausted under load] → Rate-limit walk to Gemini; consider raising wall clock only if needed.
- [VPS env not updated while image ships] → Host keeps old cached model / missing Langfuse; runbook + health fields (`configured_model`, `cached_model`, `langfuse.enabled`) make that visible.
- [IAM placeholders mistaken for usable keys] → Design and tasks forbid using `REPLACE_ME` values; rotate any key that was ever pasted into chat.

## Migration Plan

1. Apply code/docs/tests for Lightning → Gemini defaults.
2. Commit tracing + this flip on `production` (or a short-lived branch + PR).
3. Green CI; deploy with `workflow_dispatch` or a `v*` tag.
4. On the VPS: set Langfuse keys and `LLM_MODEL` / `LLM_MODEL_FALLBACKS` to match the example; recreate `api` and `worker`.
5. Verify `GET /health/ai` (`configured_model` = Lightning, `langfuse.enabled` = true) and one chat in Langfuse (`environment=production`, `rag.answer`).

## Open Questions

None that block planning. If Lightning is untitled for the production NIM key at apply time, pin the next live small NIM id after `scripts/test_nvidia_nim.py` and keep Gemini as fallback — same pattern as prior NIM retirements.
