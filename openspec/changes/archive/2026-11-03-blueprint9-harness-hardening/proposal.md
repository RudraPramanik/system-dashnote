## Why

The AI surfaces are alive on the VPS (RAG chat, LangGraph agent, HITL, LiteLLM fallback, Langfuse), but the harness is still mid-maturity: tool tenancy is prompt-trusted, there is no AI-specific budget, and orchestration has no single control-plane abstraction with typed error boundaries. Blueprint 8 locked the ship path; it does not lock a Composer-ready hardening path. Operators need one Blueprint 9 that sequences security, cost, and orchestration upgrades without breaking Alive or colliding with the reserved multi-agent Slice 9.

## What Changes

- Add `docs/documentation/blueprint9.md` as the **operator-default harness-hardening path** (grade targets, Alive law, phase order, abstraction, fallbacks, non-goals). Blueprint 8 remains the hire/ship default; Blueprint 9 is the next path after the product is alive, not a replacement.
- Add an executable detail index and per-phase Composer blueprints under `docs/documentation/blueprint/` using phase IDs **9H.*** so they stay distinct from GraphRAG Slice 8 and multi-agent Slice 9:
  - `slice9_H.md` — index and global architecture law
  - `slice9_trust.md` — 9H.1 tenant bind
  - `slice9_policy.md` — 9H.2 tool ACL + error envelopes, 9H.3 injection hygiene
  - `slice9_cost.md` — 9H.4 AI quotas
  - `slice9_resilience.md` — 9H.5 circuit/degrade + harness facade
  - `slice9_eval.md` — 9H.6 goldens that prove the grade claims
- Each phase MUST define ordered substages, a paste-first architecture law, objective prompts, validation gates, fallbacks, and error boundaries. One Composer session ≈ one substep. Later phases MUST NOT be prerequisites of earlier ones.
- Cross-link Blueprint 8 / `slice8_X.md` / `total.md` so 9H is discoverable and explicitly not Slice 9 multi-agent.
- **This change’s apply writes those planning documents only.** Runtime harness code (tool schema changes, Redis budgets, breakers, new goldens) is sequenced by the blueprint and owned by later changes.

## Capabilities

### New Capabilities

- `blueprint9-harness`: Authoritative Blueprint 9 document set — grade targets (security toward B+, cost toward B+, orchestration toward A-), locked 9H phase order, HarnessContext abstraction, fallback and error-boundary laws, and Composer-ready substages. Spec requirements govern the blueprint documents, not runtime behavior in this change.

### Modified Capabilities

- `blueprint8-ship-path`: Blueprint 8 MUST point operators to Blueprint 9 as the harness-hardening successor after the Alive ship path, without changing Tier 0 job-gate order or chat≠agent coexistence.

## Impact

- Docs only on apply: `docs/documentation/blueprint9.md`, new `docs/documentation/blueprint/slice9_*.md` files, and short pointers from `blueprint8.md`, `blueprint/slice8_X.md`, and `blueprint/total.md`.
- No API, agent graph, tool schema, Redis, dependency, or test changes in this change.
- Later applies (one phase or substep at a time) will touch `src/ai/tools/`, `src/ai/workflows/`, `src/shared/llm/`, `src/core/security/rate_limit.py` patterns, `src/observability/`, and `evals/` — only after this blueprint is the operator default.
- Assumes (recorded for design): phase IDs are `9H` not bare `9`; budgets key per-user request rate and per-workspace daily request cap, with token ceilings only when LiteLLM usage metadata exists; injection hygiene for the B+ target is delimiter wrapping plus a data-not-instructions rule, not a third-party moderation product; AI budget checks fail open on Redis errors the same way the global limiter does.
