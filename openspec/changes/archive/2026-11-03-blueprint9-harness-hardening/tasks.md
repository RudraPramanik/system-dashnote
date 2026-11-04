## 1. Operator default

- [x] 1.1 Write `docs/documentation/blueprint9.md` as the follow-this-first harness path, linking `blueprint/slice9_H.md` and each phase file, and stating Blueprint 8 stays the ship/hire default
- [x] 1.2 Document Alive law: local full-stack compose stays, `/ai/chat*` and `/ai/agent*` both remain, VPS-hostile red-team stays fixture or nightly
- [x] 1.3 Document grade targets (security toward B+, cost toward B+, orchestration toward A-) and the locked order 9H.1 → 9H.6, with later phases not prerequisites of earlier ones
- [x] 1.4 Add the HarnessContext sketch (trusted session → policy/budget → model → tools → NoteService/RagService) plus fail-closed tenant/auth and fail-open Redis budget summary
- [x] 1.5 Add explicit non-goals: multi-agent Slice 9, GraphRAG/Neo4j, chat replacing agent, billing product, second permission engine, moderation vendor, live judges in PR CI
- [x] 1.6 State that this blueprint is planning-only and grade claims wait on the 9H.6 themes

## 2. Phase index and global law

- [x] 2.1 Write `docs/documentation/blueprint/slice9_H.md` as the only phase-order source, with a table to the detail files and a sentence that 9H is not Slice 9 multi-agent and not GraphRAG Slice 8
- [x] 2.2 Add the paste-first architecture law: chat ≠ agent, tools call services only, tenant freeze from HarnessContext, HITL before create/update commit, budget fail-open on Redis, no second agent framework, fixture evals prove grades

## 3. Trust and policy detail

- [x] 3.1 Write `docs/documentation/blueprint/slice9_trust.md` with substages 9H.1.1–9H.1.4 (inventory, bind-or-overwrite fallback, HITL uses bound identity, invented-workspace golden theme), each with objective prompt, validation gate, fallback, and error boundary
- [x] 3.2 Write `docs/documentation/blueprint/slice9_policy.md` 9H.2 substages: map `notes/permissions.py` onto tools, envelope codes `forbidden` / `not_found` / `budget_exceeded` / `approval_required` / `upstream`, deny-path gate; keep HITL
- [x] 3.3 In the same policy file, write 9H.3 substages: delimiters on retrieved text and tool output, data-not-instructions hierarchy, poisoned-content golden themes; mark moderation vendor and PII redaction as non-goals

## 4. Cost, resilience, and eval detail

- [x] 4.1 Write `docs/documentation/blueprint/slice9_cost.md` with 9H.4.1–9H.4.3: per-user minute and per-workspace day request counters stricter than the global limit, optional token ceiling only when usage metadata exists, setting names without freezing integers, 429 or SSE retry contract, Redis fail-open, health checks excluded
- [x] 4.2 Write `docs/documentation/blueprint/slice9_resilience.md` with 9H.5.1–9H.5.3: degrade matrix (provider down, checkpointer down, budget exhausted), provider cooldown then existing model fallback, one control plane with thin routes
- [x] 4.3 Write `docs/documentation/blueprint/slice9_eval.md` with 9H.6.1–9H.6.3: fixture themes for invented workspace, forbidden role, poisoned content, and budget exceeded; PR CI versus nightly split; no B+/A- claim without those themes

## 5. Cross-links and sync

- [x] 5.1 Add a short successor pointer in `docs/documentation/blueprint8.md` to `blueprint9.md` that does not change Tier 0 order or chat-versus-agent coexistence, and that distinguishes 9H from multi-agent Slice 9
- [x] 5.2 Add the same disambiguation note to `docs/documentation/blueprint/slice8_X.md` and `docs/documentation/blueprint/total.md`
- [x] 5.3 Read the new files together and fix any phase-order, non-goal, or law contradiction so `slice9_H.md` wins

## 6. Docs-only gate

- [x] 6.1 Confirm this apply did not change application code, API routes, dependencies, settings values, or eval runners
- [x] 6.2 Spot-check that every substage prompt forbids replacing chat with agent and forbids breaking local `docker compose`
