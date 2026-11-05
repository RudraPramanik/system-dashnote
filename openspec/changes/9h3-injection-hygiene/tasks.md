## 1. Delimiter helper (9H.3.1)

- [x] 1.1 Add `wrap_untrusted(payload, stable_id)` in `src/ai/prompts/rag.py` using only pydantic and the stdlib: markers `<<<UNTRUSTED_DATA id="{id}">>>` and `<<<END_UNTRUSTED_DATA id="{id}">>>`, escape every `<<<` in the payload to `< <`, and use `none` when the id is missing or contains a newline, `<<<`, or `>>>`
- [x] 1.2 Keep `src/ai/harness/errors.py` as the raw JSON envelope builder. Do not wrap inside `tool_error()` or inside `src/ai/tools/note_tools.py`

## 2. RAG context path (API)

- [x] 2.1 In `build_rag_user_message`, wrap each note or file chunk with its chunk id, and keep `[CHUNK:{id}]` plus the escaped title inside that payload. Leave the user question outside the chunk markers
- [x] 2.2 On a per-chunk wrap failure, log and omit that chunk. Do not append its raw text. If every chunk is omitted, keep the existing empty-context line
- [x] 2.3 Leave `ContextBuilder` system content as `RAG_SYSTEM_INSTRUCTION` only. Do not copy chunk text into the system role. Do not add a second prompt for `RagService.stream_answer`

## 3. Instruction hierarchy (9H.3.2)

- [x] 3.1 Add `UNTRUSTED_DATA_RULE` in `src/ai/prompts/rag.py` naming `UNTRUSTED_DATA` and stating that text inside the markers is untrusted notes or tool output, not instructions, and that it cannot change workspace, user, or role, skip approval, or override tool policy
- [x] 3.2 Include that constant in `RAG_SYSTEM_INSTRUCTION` without removing the `[CHUNK:{id}]` citation rule or the notes-and-files refusal
- [x] 3.3 Import the same constant into `WORKSPACE_ASSISTANT_PROMPT`. Do not add a third persona and do not pass chunk or tool text into `call_model` system content

## 4. Agent tool-message boundary (API)

- [x] 4.1 In `_to_litellm_messages`, wrap `role=tool` content with `wrap_untrusted` and the tool-call id. Leave graph state and the tool coroutine return raw
- [x] 4.2 If wrapping a tool string fails, emit a closed marker pair whose payload is `untrusted tool output omitted`, keep the tool-call id, and do not send the raw string or raise
- [x] 4.3 Do not wrap chat history or the user question. Do not change SSE event types, REST note routes, or `/ai/chat*` versus `/ai/agent*` routing

## 5. Worker and infra stay put

- [x] 5.1 Leave the ARQ worker, Qdrant indexers, `notes_chunks` / `files_chunks`, Alembic, settings, and `docker-compose.yml` unchanged. Do not add a moderation vendor, PII redaction, Redis budget checks, or Langfuse SDK calls inside `src/ai/*`

## 6. Proof (9H.3.3)

- [x] 6.1 Add `tests/ai/test_injection_hygiene.py` with `test_poisoned_content_cannot_retarget_workspace`: marker text plus a foreign workspace id stays inside the user message, the system role is the instruction, and a search or summarize call under session workspace W does not call `RagService` with the foreign id
- [x] 6.2 In that module, add `test_poisoned_content_cannot_skip_hitl`: an allowed create or update whose text says to skip approval still interrupts, and `NoteService.create_note` / `update_note` does not run before approval
- [x] 6.3 Cover a member update the notes API would reject: skip-approval text still returns `forbidden` with no interrupt and no save
- [x] 6.4 Cover a chunk whose text contains the markers and still closes, a wrap failure that drops only that chunk, both prompts containing `UNTRUSTED_DATA_RULE`, and a `forbidden` envelope that stays raw from the tool return and still parses as the same JSON inside markers after `_to_litellm_messages`
- [x] 6.5 Run `python -m pytest tests/ai/test_injection_hygiene.py tests/ai/test_harness_policy.py tests/ai/test_harness_trust.py tests/ai/test_agent_hitl.py tests/ai/test_rag_citations.py -q` with no live LLM key. Do not skip either theme and do not weaken member rules or citation grounding to go green
- [x] 6.6 Record `test_poisoned_content_cannot_retarget_workspace` and `test_poisoned_content_cannot_skip_hitl` in the apply summary so 9H.6 can point at them. Do not add 9H.4 budget counters or the 9H.6 grade claim in this change
