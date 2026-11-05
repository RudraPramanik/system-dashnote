## Why

9H.1 binds tenant on `HarnessContext` and 9H.2 enforces note role rules with a stable tool-error envelope, but retrieved note and file text and tool strings still re-enter the model as ordinary prompt text. Blueprint 9’s next locked phase is **9H.3** (`docs/documentation/blueprint/slice9_policy.md`, indexed by `slice9_H.md`): wrap that text as untrusted data, tell the model it cannot change tenant or skip approval, and prove both with fixtures that do not need a live model. Prompt text is defense in depth. It does not replace the 9H.1 bind or the 9H.2 ACL.

## What Changes

- **9H.3.1** — Wrap retrieved note and file chunks, and tool strings fed back to the model, in start/end markers that carry a stable id when one exists. System instructions stay outside the markers. A chunk that contains the marker text still closes. If wrapping one chunk fails, that chunk is dropped and the rest continue. Chunk text is never promoted to `role=system`.
- **9H.3.2** — The RAG system prompt and the workspace assistant prompt state that text inside those markers is untrusted data. It cannot change workspace, user, or role, skip human approval, or override tool policy. No third persona. Citation grounding on `/ai/chat*` stays (`[CHUNK:{id}]` and the existing refuse line).
- **9H.3.3** — Two fixtures, no live LLM key: retrieved or tool text that names another `workspace_id` still uses the session workspace or is denied; text that says to skip approval does not commit a note without the existing HITL interrupt. A case that cannot be asserted without a hosted model is out of this change (nightly, per `slice9_eval.md`). Do not mark either fixture skipped.
- Tool failure strings from `tool_error()` stay the raw JSON envelope at the tool return. Markers go around that string only where the model message is built, and the JSON object inside stays intact. Allow and deny stay in the 9H.2 gates, not in the wrapper.
- **Out of scope:** 9H.4 Redis budgets, 9H.5 degrade, 9H.6’s full grade suite and claim rule, a moderation vendor, PII redaction, chat-route replacement, OPA/Cedar, Alembic, compose changes, Slice 8, Slice 9.

## Capabilities

### New Capabilities

- `ai-harness-injection`: Delimiters for retrieved chunks and tool outputs, the data-not-instructions rule on the existing RAG and workspace-assistant prompts, and the two poisoned-content fixtures.

### Modified Capabilities

- `ai-harness-policy`: The failure envelope remains the tool return. When that string is placed in a model message it is wrapped as untrusted data, and `code` stays readable inside the markers. The wrapper MUST NOT decide allow or deny.
- `agent-hitl`: Text that tells the model to skip approval MUST NOT skip the interrupt or persist a create/update. A forbidden role still does not reach HITL.

## Impact

- Code: `src/ai/prompts/rag.py` (`build_rag_user_message`, `RAG_SYSTEM_INSTRUCTION`) and `src/ai/workflows/workspace_assistant.py` (assistant prompt and the tool-message boundary in `_to_litellm_messages`). `ContextBuilder` already calls `build_rag_user_message`, so both `RagService.answer` and `stream_answer` pick up chunk markers without a second prompt. `src/ai/harness/errors.py` stays the unwrapped envelope builder. Tools still call `NoteService` or `RagService` only.
- APIs: `/ai/chat*` and `/ai/agent*` both remain. Chat context formatting and the two system prompts change. SSE event types do not. Citation objects (`source_type`, ids) do not. No HTTP contract change for REST notes.
- Tenancy: workspace, user, and role still come only from `HarnessContext`. Role checks from 9H.2 stay fail-closed. Redis is not a dependency. No new Qdrant write and no collection change (`notes_chunks` / `files_chunks`).
- Tests: add `tests/ai/test_injection_hygiene.py`. Keep `tests/ai/test_harness_policy.py`, `tests/ai/test_harness_trust.py`, `tests/ai/test_agent_hitl.py`, and `tests/ai/test_rag_citations.py` green. No live model key.
- Blueprint map: **9H.3.1 → 9H.3.2 → 9H.3.3** only. 9H.6 may later point at these fixtures; this change does not implement 9H.6.
