# Slice 4 — Polish: Streaming + Citations
## Final Cursor Prompts (Gemini 2.5 Flash, SSE, Production-Safe)

> **Context carried from previous slices**
> - Slice 3 gate passed: `POST /ai/chat` returns grounded answer + citations ✅
> - `RagService.answer()` in `src/ai/services/rag_service.py` — DO NOT TOUCH
> - `RAGAnswer`, `RAG_SYSTEM_INSTRUCTION`, `build_rag_user_message` in `src/ai/prompts/rag.py`
> - Chat route in `src/ai_routes/chat.py` — append only
> - `WorkspaceVectorSearch` singleton via `get_workspace_vector_search()`
> - Import style: `from config import settings` (never `from src.config`)
> - Stack uses Nginx — SSE headers must explicitly disable buffering
> - `POST /ai/chat` (non-streaming) must remain fully functional after this slice

---

## ARCHITECTURE LAW
### Paste as your FIRST message in every Cursor Composer session.

```
ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

MODULE PATHS:
  Import as: from config import settings, get_settings
             from ai.services.rag_service import RagService, get_rag_service
             from ai.prompts.rag import RAG_SYSTEM_INSTRUCTION, build_rag_user_message
             from core.security.dependency import get_current_context
  NEVER as:  from src.config import ...
             from src.ai.services import ...

STREAMING LAWS:
  1. stream_answer() accepts plain strings (workspace_id, user_id, role)
     NEVER RequestContext — required for LangGraph tool reuse in Slice 6
  2. RequestContext is frozen to plain strings in the ROUTE before generator opens
     workspace_id = str(ctx.workspace_id)
     user_id = str(ctx.user_id)
     role = ctx.role
     ctx is NEVER referenced inside async def generate()
  3. RagService singleton is resolved BEFORE the generator function is defined
     rag = get_rag_service()  ← resolved here, in route handler scope
     async def generate():
         async for chunk in rag.stream_answer(...):  ← rag captured by closure
  4. Nginx buffering must be disabled for SSE to work end-to-end:
     Headers: Cache-Control: no-cache, X-Accel-Buffering: no
     Without these, Nginx holds the full response before forwarding = no streaming

PROMPT LAW:
  - ONE system instruction for both streaming and non-streaming: RAG_SYSTEM_INSTRUCTION
  - No streaming-specific prompt variant — same instruction, stream=True is the only diff
  - Never add inline [CHUNK:uuid] parsing from token stream — unreliable mid-stream
  - Citations come from retrieval grounding at stream END, not from LLM token parsing

SERVICE LAW — src/ai/services/rag_service.py:
  - APPEND ONLY — never touch existing answer() method or existing models
  - stream_answer() is a NEW method added below existing code
  - No FastAPI, RequestContext, SQLAlchemy in this file

ROUTE LAW — src/ai_routes/chat.py:
  - APPEND ONLY — POST /ai/chat must remain fully functional
  - POST /ai/chat/stream is a NEW endpoint appended below existing route
  - Do not restructure, reorder, or rewrite existing route logic

INFRA LAW:
  - No new packages needed — litellm already handles streaming
  - No new Dockerfiles or compose files
  - Append-only to requirements.txt only if a package is genuinely missing

LangGraph compatibility:
  stream_answer() signature is agent-tool-compatible:
  (question, workspace_id, user_id, role) as plain strings.
  Slice 6 agent tools call this with no adapter needed.

Acknowledge these laws before writing any code.
```

---

## Sub-step 4.1 — Streaming Core Service

**Goal:**
- `StreamToken` and `StreamMetadata` typed models defined
- `stream_answer()` async generator method appended to `RagService`
- Same retrieval + RBAC + token budget logic as `answer()`
- Streams text tokens as they arrive, yields citation metadata at end
- Citations grounded against retrieved set — never from LLM token parsing

**Files to open in Cursor:**
- `src/ai/services/rag_service.py`
- `src/ai/prompts/rag.py` (reference only — no changes)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 4.1 — Append stream_answer() async generator method
to the existing RagService class. The existing answer() method must remain
completely unchanged.

CONTEXT:
- Existing RagService.answer() is in src/ai/services/rag_service.py
- Same retrieval logic: WorkspaceVectorSearch + build_rbac_filter
- Same prompt: RAG_SYSTEM_INSTRUCTION + build_rag_user_message (no new prompt)
- Same token budget logic: TOKEN_BUDGET_PER_REQUEST chars of context
- litellm.acompletion(stream=True) for token streaming
- Citations: grounded at stream END against retrieved chunks — NOT parsed from tokens
- Model: settings.LLM_MODEL (gemini/gemini-2.5-flash)

LAWS IN EFFECT:
- APPEND ONLY to rag_service.py — answer() and all existing code untouched
- stream_answer() accepts plain strings: workspace_id, user_id, role
  NEVER RequestContext — LangGraph tool compatibility
- No new prompt variant — RAG_SYSTEM_INSTRUCTION is used as-is
- No [CHUNK:uuid] inline parsing from token stream — fragile, unreliable
- Citations yielded as final metadata packet from grounding logic, not LLM output

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — Add stream event type models to rag_service.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Append these models to src/ai/services/rag_service.py AFTER the existing
ChatResult model and BEFORE the RagService class definition.
Check they do not already exist before adding.

# ── Slice 4: Streaming event models ─────────────────────────────────────────

from typing import Literal, AsyncGenerator   # add to existing imports if missing

class StreamToken(BaseModel):
    """
    A single token chunk yielded during streaming.
    type is always "token" — lets the client distinguish from metadata.
    """
    model_config = ConfigDict(frozen=True)

    type: Literal["token"] = "token"
    content: str   # may be empty string for keep-alive chunks — client should skip


class StreamMetadata(BaseModel):
    """
    Final packet yielded after all tokens are streamed.
    Contains grounded citations and performance metrics.
    type is always "metadata" — client renders citations after stream completes.
    """
    model_config = ConfigDict(frozen=True)

    type: Literal["metadata"] = "metadata"
    citations: list[Citation]
    chunks_retrieved: int
    chunks_used: int
    latency_ms: float


# Union type for the generator yield type
StreamEvent = StreamToken | StreamMetadata

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Append stream_answer() to RagService class
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Append this method INSIDE the RagService class, after the existing answer() method.
Do NOT modify answer() in any way.

    async def stream_answer(
        self,
        *,
        question: str,
        workspace_id: str,
        user_id: str,
        role: str,
        retrieval_limit: int = 8,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream a RAG answer as progressive token events.

        Yields:
            StreamToken events as text arrives from the LLM.
            One final StreamMetadata event with citations and metrics.

        Citation strategy:
            Citations are grounded against retrieved chunks at stream end.
            We do NOT parse [CHUNK:uuid] tags from the token stream — this
            is fragile and unreliable mid-stream. Instead, top retrieved
            chunks become citations after streaming completes.

        LangGraph compatibility:
            Same plain string signature as answer() — works from both
            HTTP routes (Slice 4) and agent tools (Slice 6) unchanged.

        Args:
            question:        User's natural language question.
            workspace_id:    From RequestContext.workspace_id — plain string.
            user_id:         From RequestContext.user_id — plain string.
            role:            "owner" | "admin" | "member" — plain string.
            retrieval_limit: Max chunks to retrieve before streaming.
        """
        start = time.monotonic()
        settings = get_settings()

        # ── Step 1: retrieve relevant chunks (same as answer()) ─────────────
        retrieved: list[SearchResult] = await self._searcher.search(
            query_text=question,
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            limit=retrieval_limit,
        )

        if not retrieved:
            logger.info(
                "stream_answer: no relevant chunks found",
                extra={"workspace_id": workspace_id},
            )
            yield StreamToken(content="I could not find relevant information in your notes for this query.")
            yield StreamMetadata(
                citations=[],
                chunks_retrieved=0,
                chunks_used=0,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )
            return

        # ── Step 2: enforce token budget (same as answer()) ─────────────────
        budget = settings.TOKEN_BUDGET_PER_REQUEST
        context_chunks: list[dict] = []
        chars_used = 0

        for result in retrieved:
            chunk_chars = len(result.chunk_text)
            if chars_used + chunk_chars > budget:
                break
            context_chunks.append({
                "chunk_id": result.chunk_id,
                "note_id": result.note_id,
                "title": result.title,
                "text": result.chunk_text,
                "score": result.score,
            })
            chars_used += chunk_chars

        # ── Step 3: build prompt (same template, no streaming variant) ───────
        user_message = build_rag_user_message(question, context_chunks)

        # ── Step 4: stream LiteLLM completion ───────────────────────────────
        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_INSTRUCTION},
                    {"role": "user", "content": user_message},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )
        except Exception as e:
            logger.error(
                "LLM streaming failed",
                extra={
                    "model": settings.LLM_MODEL,
                    "workspace_id": workspace_id,
                    "error": str(e),
                },
            )
            raise

        # ── Step 5: yield token events as they arrive ────────────────────────
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield StreamToken(content=delta)

        # ── Step 6: ground citations and yield metadata ──────────────────────
        # Citations from retrieval — never from LLM token parsing
        citations: list[Citation] = [
            Citation(
                note_id=c["note_id"],
                chunk_id=c["chunk_id"],
                title=c["title"],
                relevance_score=c["score"],
            )
            for c in context_chunks[:5]   # top 5 retrieved chunks as citations
        ]

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "stream_answer complete",
            extra={
                "workspace_id": workspace_id,
                "chunks_retrieved": len(retrieved),
                "chunks_used": len(context_chunks),
                "citations_count": len(citations),
                "model": settings.LLM_MODEL,
                "latency_ms": latency_ms,
            },
        )

        yield StreamMetadata(
            citations=citations,
            chunks_retrieved=len(retrieved),
            chunks_used=len(context_chunks),
            latency_ms=latency_ms,
        )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Update __main__ validation block
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find the existing if __name__ == "__main__" block at the bottom
of src/ai/services/rag_service.py.
REPLACE the entire block with this updated version that validates both
answer() and stream_answer() imports without making real API calls:

if __name__ == "__main__":
    # Validation: docker compose exec -e PYTHONPATH=/app/src api python -m ai.services.rag_service
    import asyncio

    async def _validate() -> None:
        print("RagService Slice 4 import validation...")

        # Verify Slice 3 models still present
        from ai.services.rag_service import (
            Citation, ChatResult, get_rag_service,
            StreamToken, StreamMetadata, StreamEvent,
        )
        print("PASS: all models importable (Citation, ChatResult, StreamToken, StreamMetadata)")

        # Verify StreamToken model
        token = StreamToken(content="Hello")
        assert token.type == "token"
        assert token.content == "Hello"
        print("PASS: StreamToken model valid")

        # Verify StreamMetadata model
        meta = StreamMetadata(
            citations=[],
            chunks_retrieved=3,
            chunks_used=2,
            latency_ms=1200.5,
        )
        assert meta.type == "metadata"
        assert meta.chunks_retrieved == 3
        print("PASS: StreamMetadata model valid")

        # Verify empty StreamToken is safe (keep-alive chunks)
        empty_token = StreamToken(content="")
        assert empty_token.content == ""
        print("PASS: empty StreamToken is safe (client should skip)")

        # Verify service has stream_answer method
        service = get_rag_service()
        assert hasattr(service, "stream_answer"), "FAIL: stream_answer() not found on RagService"
        assert hasattr(service, "answer"), "FAIL: answer() was accidentally removed"
        print("PASS: RagService has both answer() and stream_answer() methods")

        print(f"PASS: LLM model configured: {get_settings().LLM_MODEL}")
        print("PASS: Slice 4 service layer validation complete — ready for 4.2")

    asyncio.run(_validate())

OUTPUT FORMAT:
Show all three tasks clearly labelled.
For Task 1 and 2: show exactly where in the file to insert (e.g., "after line
containing 'class RagService'", "after the answer() method closing line").
For Task 3: show the full replacement __main__ block.
Zero truncation. No placeholder comments.
```

**Validation:**
```powershell
docker compose build api
# Expected: clean build

docker compose exec -e PYTHONPATH=/app/src api python -m ai.services.rag_service
# Expected:
#   PASS: all models importable (Citation, ChatResult, StreamToken, StreamMetadata)
#   PASS: StreamToken model valid
#   PASS: StreamMetadata model valid
#   PASS: empty StreamToken is safe (client should skip)
#   PASS: RagService has both answer() and stream_answer() methods
#   PASS: LLM model configured: gemini/gemini-2.5-flash
#   PASS: Slice 4 service layer validation complete — ready for 4.2
```

**Commit:**
```bash
git commit -am "feat(slice4.1): append stream_answer() to rag_service, typed stream events"
```

---

## Sub-step 4.2 — SSE Streaming Route

**Goal:**
- `POST /ai/chat/stream` endpoint appended to `src/ai_routes/chat.py`
- `ctx` frozen to primitives before generator opens
- `RagService` singleton resolved before generator — captured by closure
- Nginx buffering disabled via response headers
- `POST /ai/chat` unchanged and still functional
- Live token streaming confirmed in terminal

**Files to open in Cursor:**
- `src/ai_routes/chat.py`
- `src/main.py` (reference only — no changes needed)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 4.2 — Append POST /ai/chat/stream SSE endpoint to
the existing chat router. The existing POST /ai/chat must remain
completely unchanged.

CONTEXT:
- Existing POST /ai/chat is in src/ai_routes/chat.py — DO NOT TOUCH IT
- RagService.stream_answer() yields StreamToken | StreamMetadata events
- StreamToken: {"type": "token", "content": str}
- StreamMetadata: {"type": "metadata", "citations": [...], ...}
- Stack uses Nginx — must set headers to disable response buffering
  Without Cache-Control: no-cache and X-Accel-Buffering: no,
  Nginx will buffer the entire stream before forwarding = no streaming
- RagService singleton resolved BEFORE generator opens (not inside it)
- ctx frozen to plain strings BEFORE generator opens (not inside it)

LAWS IN EFFECT:
- APPEND ONLY to src/ai_routes/chat.py
- POST /ai/chat endpoint must remain exactly as written in Slice 3
- ctx is NEVER referenced inside async def generate()
- get_rag_service() is called OUTSIDE generate() — captured by closure
- Headers Cache-Control: no-cache and X-Accel-Buffering: no are MANDATORY
- No new imports to main.py — ai_chat_router already registered

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — Append POST /ai/chat/stream to src/ai_routes/chat.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/ai_routes/chat.py carefully.
Find the end of the existing POST /ai/chat route handler.
Append the following AFTER it — do not modify anything above.

Add these imports at the top of the file if not already present:
  import json
  from fastapi.responses import StreamingResponse
  from ai.services.rag_service import StreamToken, StreamMetadata, StreamEvent

Then append this complete route at the bottom of the file:

@router.post(
    "/chat/stream",
    summary="Stream a workspace question answer (SSE)",
    description=(
        "Server-Sent Events streaming version of /ai/chat. "
        "Yields token chunks progressively, then a final metadata event "
        "with citations. Use /ai/chat for non-streaming clients."
    ),
    response_class=StreamingResponse,
)
async def chat_stream(
    body: ChatRequest,
    ctx: RequestContext = Depends(get_current_context),
    rag: RagService = Depends(get_rag_service),
) -> StreamingResponse:
    """
    Stream a RAG answer using Server-Sent Events.

    Event format:
        data: {"type": "token", "content": "..."}\n\n
        data: {"type": "token", "content": "..."}\n\n
        ... (one event per token)
        data: {"type": "metadata", "citations": [...], "latency_ms": N}\n\n
        data: [DONE]\n\n

    Security:
        ctx.workspace_id sourced from JWT — never from request body.
        Frozen to plain string BEFORE generator opens — ctx never
        referenced inside generate() to prevent mid-stream access issues.

    Nginx note:
        X-Accel-Buffering: no disables Nginx proxy buffering.
        Cache-Control: no-cache prevents intermediate caching.
        Both headers are required for tokens to stream progressively.

    LangGraph note:
        rag.stream_answer() is also callable from agent tools in Slice 6.
        The HTTP wrapper here does not affect the service signature.
    """
    # ── Step 1: Freeze security context BEFORE generator opens ──────────────
    # ctx must never be referenced inside generate().
    # Plain string primitives are safe to use inside async generators.
    workspace_id = str(ctx.workspace_id)   # from JWT wid claim
    user_id = str(ctx.user_id)             # from JWT sub claim
    role = ctx.role                         # "owner" | "admin" | "member"

    # ── Step 2: Resolve service singleton BEFORE generator opens ────────────
    # get_rag_service() is already called via Depends(get_rag_service) above.
    # rag is captured by closure — no instantiation inside generate().

    async def generate():
        """
        SSE generator — yields data: {...}\\n\\n frames.

        Security: only frozen primitives (workspace_id, user_id, role) used.
        ctx is never referenced here. rag singleton captured by closure.
        """
        try:
            async for event in rag.stream_answer(
                question=body.message,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
            ):
                # Serialize StreamToken or StreamMetadata to JSON
                yield f"data: {event.model_dump_json()}\n\n"

        except Exception as e:
            # Yield an error event so the client knows the stream failed
            # Never silently drop errors mid-stream
            error_payload = json.dumps({
                "type": "error",
                "message": "Stream encountered an error. Please try again.",
            })
            yield f"data: {error_payload}\n\n"

        finally:
            # Always emit [DONE] — lets client close the EventSource connection
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",           # prevent intermediate caching
            "X-Accel-Buffering": "no",             # disable Nginx proxy buffering
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )

Show me the exact lines appended and confirm existing POST /ai/chat is unchanged.
Generate the complete addition — zero truncation.
```

**Validation — Slice 4 Gate:**
```powershell
docker compose up -d --build api

# Step 1: verify non-streaming still works (must not be broken)
Invoke-RestMethod `
  -Uri "http://127.0.0.1/ai/chat" `
  -Method Post `
  -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body '{"message": "What is in my notes?"}'
# Expected: same JSON response as Slice 3 — answer + citations

# Step 2: test streaming endpoint with curl (--no-buffer = see tokens as they arrive)
curl.exe -sS -X POST http://127.0.0.1/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message": "Summarize my workspace notes on project plans."}' `
  --no-buffer

# GATE 1 — Progressive tokens visible:
# Output must appear word-by-word in terminal, NOT all at once
# Each line: data: {"type":"token","content":"..."}
# If full response appears at once: Nginx buffering is active
# Fix: verify X-Accel-Buffering: no header is being sent

# GATE 2 — Final metadata event:
# Second-to-last line before [DONE] must be:
# data: {"type":"metadata","citations":[...],"chunks_retrieved":N,...}
# citations array must have note_id, title, chunk_id, relevance_score

# GATE 3 — Stream closes cleanly:
# Last line: data: [DONE]
# No hanging connection after [DONE]

# GATE 4 — Empty workspace returns graceful message:
# Use token from workspace with no notes
# Expected first event: data: {"type":"token","content":"I could not find..."}
# Expected final event: data: {"type":"metadata","citations":[],...}
# Then: data: [DONE]

# GATE 5 — Non-streaming endpoint unchanged:
# POST /ai/chat still returns JSON response (not SSE)

# GATE 6 — API health unchanged:
curl.exe -sS http://127.0.0.1/health
# Expected: {"status":"ok",...}
```

**If Nginx buffers the stream (Gate 1 fails):**
```powershell
# Confirm header is being sent:
curl.exe -sS -I -X POST http://127.0.0.1/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message":"test"}'
# Look for: X-Accel-Buffering: no in response headers
# If missing: verify the headers dict in StreamingResponse is correct

# Alternative: test directly against API port (bypasses Nginx):
curl.exe -sS -X POST http://127.0.0.1:8000/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message":"test"}' `
  --no-buffer
# If streaming works on :8000 but not :80 → Nginx config needs proxy_buffering off
```

**Nginx config fix if needed (nginx/default.conf):**
```nginx
# Add inside the location / block if X-Accel-Buffering header is not respected:
proxy_buffering off;
proxy_cache off;
```

**Commit:**
```bash
git commit -am "feat(slice4.2): sse streaming endpoint, nginx buffering disabled — slice 4 complete"
```

---

## Slice 4 Complete — What Was Built

```
src/ai/services/rag_service.py   ← APPENDED: StreamToken, StreamMetadata,
                                    StreamEvent models
                                    stream_answer() async generator method
                                    Updated __main__ validation block

src/ai_routes/chat.py            ← APPENDED: POST /ai/chat/stream endpoint
                                    SSE generator with frozen ctx
                                    Nginx buffering headers

Everything from Slice 3 unchanged:
  POST /ai/chat                  ← still fully functional
  RagService.answer()            ← untouched
  RAGAnswer schema               ← untouched
  RAG_SYSTEM_INSTRUCTION         ← untouched (no streaming variant added)
```

```
What is NOT in Slice 4 (correct — belongs to later slices):
  ✗ thread_id / conversation memory (Slice 5)
  ✗ LangGraph imports (Slice 6)
  ✗ LangSmith active tracing (Slice 10)
  ✗ Better prompts based on real usage — tune after Slice 5 when
    you have real conversation data to learn from
```

---

## SSE Client Reference (for frontend integration)

```javascript
// How a frontend would consume POST /ai/chat/stream
const response = await fetch('/ai/chat/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ message: question }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;
    const data = line.slice(6);
    if (data === '[DONE]') break;

    const event = JSON.parse(data);
    if (event.type === 'token' && event.content) {
      // append token to displayed text
      appendToResponse(event.content);
    }
    if (event.type === 'metadata') {
      // render citations after stream completes
      renderCitations(event.citations);
    }
    if (event.type === 'error') {
      // show error message
      showError(event.message);
    }
  }
}
```

---

> **Next:** Slice 5 — Memory
> Add `ai_threads` and `ai_messages` tables (Alembic migration).
> `POST /ai/chat` and `/ai/chat/stream` accept optional `thread_id`.
> Recent messages injected into context before retrieval.
> `GET /ai/threads` and `GET /ai/threads/{id}/messages` for UI.
> LangGraph's `AsyncPostgresSaver` wired but kept separate from product tables.