## Context

See proposal.md for why. Requirements live in `specs/ai-harness-injection/spec.md`, `specs/ai-harness-policy/spec.md`, and `specs/agent-hitl/spec.md`.

9H.1 and 9H.2 already freeze tenant on `HarnessContext` and return tool failures from `tool_error()` in `src/ai/harness/errors.py` as a raw JSON string. Success stays prose. `create_note` and `update_note` still interrupt before `NoteService` writes. Chat and the agent search path both build model context through `ContextBuilder` → `build_rag_user_message()` (`src/ai/prompts/rag.py`). `RagService.answer` and `stream_answer` both use that builder. The agent sends tool results back to the model only from `_to_litellm_messages()` in `src/ai/workflows/workspace_assistant.py`.

`ai/prompts/rag.py` may import only pydantic and the stdlib. It cannot import `ai.harness`. `errors.py` is stdlib-only and must stay the unwrapped envelope builder so `tests/ai/test_harness_policy.py` keeps parsing JSON from the tool return.

This work runs in the API process: the RAG context builder and the LangGraph agent node. It does not run on the ARQ worker. No Qdrant read or write change. Collections stay `notes_chunks` and `files_chunks`. No Alembic, settings, or compose change.

## Goals / Non-Goals

**Goals:**

- One stdlib wrapper both chat context and agent tool messages can use without an import-law break.
- The same data-not-instructions sentence on the two prompts that already exist.
- Two pytest fixtures, no live LLM key, that fail if a foreign workspace is queried or a note commits without HITL.

**Non-Goals:**

- Deciding allow or deny inside the wrapper. 9H.2 gates stay where they are.
- Wrapping prior chat history or the user’s own question. Only retrieved chunks and tool strings.
- 9H.4 counters, 9H.5, 9H.6’s grade claim, a moderation vendor, or PII redaction.
- A new SSE event, a new persona, or a second agent framework.

## Decisions

### 1. Wrapper lives in the prompt module

**Choice:** Add `wrap_untrusted(payload, stable_id)` in `src/ai/prompts/rag.py`. `build_rag_user_message` calls it per chunk. `_to_litellm_messages` imports it and wraps `role=tool` content. The tool coroutine and `tool_error()` stay raw.

**Why:** `rag.py` cannot import `ai.harness`, and both chat paths already format chunks in `build_rag_user_message`. The agent graph can import `ai.prompts.rag`. One helper satisfies the blueprint fallback without a router import and without duplicating the escape rules.

**Alternatives:** A helper in `ai/harness/` (rag.py cannot import it — rejected). Duplicating five lines in the graph and the prompt file (the escape rule would drift — rejected). Wrapping inside `note_tools` (policy tests would stop seeing raw JSON — rejected).

Markers:

```
<<<UNTRUSTED_DATA id="{id}">>>
{escaped payload}
<<<END_UNTRUSTED_DATA id="{id}">>>
```

`stable_id` is the chunk id for retrieval and the tool-call id for a tool message. Missing or unsafe ids use `none`. An id is unsafe when it contains a newline, `<<<`, or `>>>`. Do not put the raw id into the marker in that case.

Escape the payload before wrapping: replace every `<<<` with `< <` so neither marker can occur intact inside the text. Then append the real end marker. A chunk that contains the marker strings still has exactly one closing marker for that id, and that closer is the wrapper’s.

Keep the existing citation line inside the payload, above the escaped body:

`[CHUNK:{id}] (from: {title})`

Title is escaped the same way as the body. Do not parse `[CHUNK:…]` from the token stream. Server-side citation grounding in `RagService` stays matched against the retrieved set.

### 2. Where each kind of text is wrapped

```
retrieved chunk
    │
    ▼
build_rag_user_message          one marker pair per chunk
    │                           question stays after the context block, unwrapped
    ▼
ContextBuilder                  system message = RAG_SYSTEM_INSTRUCTION only
    │
    ├─ /ai/chat*  ─────────────► chat model
    └─ RagService.answer        agent search/summarize (inner RAG call)

tool coroutine return           raw prose or raw JSON envelope
    │
    ▼
graph state                     still raw (policy tests read this)
    │
    ▼
_to_litellm_messages            wrap role=tool only, then LiteLLM
```

`call_model` system text is the assistant prompt plus the three server-bound session fields already on agent state. Do not interpolate chunk text or tool text into that string.

Per chunk, catch any wrap failure, log it, and omit that chunk. Do not append its raw text. If every chunk is omitted, keep today’s empty-context line. Never raise out of message building because of one chunk.

If wrapping a tool string fails, still emit a closed marker pair whose payload is the fixed text `untrusted tool output omitted`, with the same tool-call id. Do not send the raw string and do not raise. The tool-call id on the message stays so the provider can pair the result.

### 3. One sentence, two prompts

**Choice:** A constant `UNTRUSTED_DATA_RULE` in `rag.py`, included in `RAG_SYSTEM_INSTRUCTION` and imported into `WORKSPACE_ASSISTANT_PROMPT`.

The sentence names `UNTRUSTED_DATA` and states that text inside those markers is untrusted notes or tool output, not instructions, and that it cannot change workspace, user, or role, skip approval, or override tool policy.

Leave the existing RAG rules in place, including cite-`[CHUNK:{id}]` and the “notes and files” refusal. Leave the assistant’s existing tool rules in place, including “do not pass workspace_id, user_id, or role”. Do not add a third persona and do not move the assistant prompt into the RAG module.

**Why:** `rag.py` is the only prompt module the graph is allowed to import, and the blueprint fallback is one shared sentence when import laws allow it.

**Alternatives:** A prompt-management service (rejected). Copying the sentence by hand into both files (drifts — rejected unless the import is later found illegal).

### 4. Poisoned-content fixtures do not call a model

Add `tests/ai/test_injection_hygiene.py`. Drive the message builder and the existing tool coroutines with a set `HarnessContext` and fakes, same style as `tests/ai/test_harness_policy.py`. No live LLM key. Do not `pytest.skip` either theme.

| Test | Setup | Failure condition |
|------|--------|-------------------|
| `test_poisoned_content_cannot_retarget_workspace` | Chunk and tool/query text name a foreign workspace id and include the marker strings. Session workspace is W. | System role contains the chunk, the wrapper does not close, or `RagService` / `NoteService` is called with the foreign id. |
| `test_poisoned_content_cannot_skip_hitl` | Allowed role. Create or update content says to skip approval and write now. | `NoteService.create_note` or `update_note` runs without the existing interrupt. |

Also cover, in the same module: a member update that the notes API would reject still returns `forbidden` with no interrupt when the text says to skip approval; a chunk that cannot be wrapped is omitted while a sibling chunk remains delimited; both prompts contain `UNTRUSTED_DATA_RULE`; a failure envelope placed through `_to_litellm_messages` still parses as the same JSON object inside the markers. The tool return before that conversion stays raw, so the 9H.2 policy tests do not need a new parser.

Name the two theme tests in the apply summary so 9H.6 can point at them. Do not add the 9H.6 grade claim or the other two themes (invented tool-argument workspace is already 9H.1; budget exceeded is 9H.4).

### 5. What this change must not move

Role allow-list, `NoteService` manage checks, missing-harness `forbidden`, and HITL interrupt stay in `note_tools.py`. The wrapper does not read `code`. User reject stays the existing non-commit string. Checkpointer-unavailable stays the existing blocked-mutation signal.

9H.4 will return `budget_exceeded` from `tool_error()` and will be wrapped automatically because every tool message passes `_to_litellm_messages`. It must not add a second envelope or a second wrapper.

## Risks / Trade-offs

- [The model still obeys text inside the markers] → Accepted. The prompt is defense in depth. Fixtures assert tenant and HITL in code, not model compliance. A live jailbreak stays nightly (`slice9_eval.md`) and is not this change.
- [User questions and history stay unwrapped] → The user is allowed to instruct the assistant. Retrieved notes and tool output are not. Do not wrap history in this slice.
- [Escaping `<<<` changes a chunk the user wrote] → The model sees a broken marker, not a new instruction boundary. Citation ids stay on the `[CHUNK:{id}]` line. Grounding still uses the retrieved set, not the model’s copy of the text.
- [Inner RAG answer is wrapped again as a tool message] → The agent model sees the answer as data, not the raw chunks. The inner call already saw delimited chunks. Do not also paste raw chunks into the assistant system prompt.
- [Policy tests start failing because they parse tool messages after conversion] → They call the tool coroutine. Keep `tool_error()` raw. Add one conversion test instead of changing those assertions.
- [`RAG_SYSTEM_INSTRUCTION` edits affect eval style scores] → Add only the shared sentence. Do not rewrite tone, the refusal line, or the citation rule to chase a score.
- [Scope creep into budgets or goldens] → 9H.4 and 9H.6 are named above as consumers, not work.

## Migration Plan

1. Land `wrap_untrusted` and use it in `build_rag_user_message`, including the escape and the per-chunk drop.
2. Add `UNTRUSTED_DATA_RULE` to both prompts.
3. Wrap tool messages in `_to_litellm_messages` only.
4. Add the injection tests and re-run the policy, trust, HITL, citation, and injection modules.
5. Rollback is reverting the change. No migration, no feature flag, no Redis key.

## Open Questions

None that change the specs or the task split. The exact log message on a dropped chunk can follow whatever structured `extra=` style the file already uses.
