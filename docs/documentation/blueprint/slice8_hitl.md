# Slice 8X.3 — HITL API-First (Agent Mutations)
## Final Cursor Prompts (4 Sub-steps, Raise Autonomy Safely, No FE Required)

> **Parent index:** [`slice8_X.md`](slice8_X.md)  
> **Code anchors:** `src/ai_routes/agent.py` · `src/ai/workflows/workspace_assistant.py` · `src/ai/tools/note_tools.py` · `src/ai/memory/checkpointer.py` · [`ai.md`](../ai.md) Slice 6  
> **When to run:** After **8X.1** (recommended) and **8X.2** agent trajectory thinking (recommended).  
> **Goal:** Human approval before `create_note` / `update_note` side effects — API + SSE + script/tests. **No** polished Next.js console for this gate.

---

## Slice Overview

```
8X.3.1  Interrupt          before create/update tool side effects (graph)
8X.3.2  SSE event          approval_required aligned with existing stream types
8X.3.3  Resume             continue by thread_id / checkpointer
8X.3.4  Smoke + tests      curl/script approve vs reject; FE still forbidden
```

**One Composer session ≈ one substep.**

---

## Readiness gate (before 8X.3.1)

| Prerequisite | Expected | Action if missing |
|--------------|----------|-------------------|
| Slice 6 agent | `POST /ai/agent`, `/ai/agent/stream` work | Finish Slice 6 |
| Checkpointer | `init_checkpointer` / thread_id config | Read `ai/memory/checkpointer.py` |
| Mutation tools | create/update via `NoteService` | Do not shortcut to repositories |
| Chat routes | Untouched coexistence | Never replace chat with agent |
| 8X.2 traj “forbid surprise create” | Recommended | Informs what HITL still must catch |
| Frontend | **Not required** | 8X.5 / B-gate later |

**Verdict:** Start **8X.3.1** only after reading current stream event shapes in `ai_routes/agent.py`.

---

## ARCHITECTURE LAW — Slice 8X.3 HITL
### Paste as your FIRST message in every Composer session for 8X.3.x

```
ARCHITECTURE LAW — DashNoteSystem Slice 8X.3 (HITL API-first).

CHAT ≠ AGENT:
  src/ai_routes/chat.py — NEVER modified to become the agent.
  POST /ai/chat* remains the fast RAG path.
  HITL applies to /ai/agent* mutation path only (unless explicitly extending later).

TOOL CHAIN:
  Tools → NoteService / RagService → repositories.
  Never call repositories directly from tools or interrupt handlers.

TENANT FREEZE:
  workspace_id, user_id, role from trusted RequestContext / graph state only.
  Model tool args must not override tenant identity.

CHECKPOINTER:
  Reuse existing LangGraph checkpointer + thread_id.
  Do not invent a second persistence system for interrupts.
  Checkpointer ≠ product AIThread ORM tables (laws in ai.md).

SSE / STREAM:
  Read ai_routes/agent.py current event types first
  (token, tool_start, tool_end, done, error — verify in code).
  Proposed new event: type "approval_required"
  with tool name, args summary, thread_id, interrupt/resume id.
  If naming must change to fit existing taxonomy, document the final name.

FE OUT OF SCOPE:
  Polished Next.js approval UI is NOT required for 8X.3 gate.
  Script/curl (+ tests) are enough.

FALLBACK:
  If LangGraph interrupt APIs differ from assumptions → read installed
  LangGraph version docs / existing graph code; invent minimally.
  If resume cannot share thread_id → STOP and report; do not silently
  drop mutations without user-visible control.
```

---

## Fallbacks / out of scope

| Out of scope | Defer to |
|--------------|----------|
| Next.js approval console | 8X.5 / `frontendguide.md` B5 |
| Multi-agent / supervisor | Slice 9 |
| Automation worker approval queue (7A) | Optional later — different surface |
| Replacing chat with agent | Never |
| Claiming production-live | 7P.8 smoke |

**Proposed stream contract (confirm in implement):**

```
Existing (approx):  token | tool_start | tool_end | done | error
Add:                approval_required
Resume:             client confirms → resume graph with same thread_id
Reject:             end turn; no mutation side effect
```

---

## Sub-step 8X.3.1 — Interrupt before mutations

**Goal:** Graph pauses before `create_note` / `update_note` (or equivalent) commits side effects.

**Read first:** `workspace_assistant.py`, `note_tools.py`, LangGraph interrupt patterns for your pinned version.

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.1 — Interrupt before agent note mutation side effects.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: readiness gate passed; read agent graph + tools.

TASKS:
  1. Identify create/update tool execution path in the graph ToolNode / wrappers.
  2. Add interrupt (or equivalent) BEFORE NoteService create/update side effects.
  3. Ensure search/summarize tools are not blocked by mutation HITL.
  4. Keep chat routes and RagService chat path untouched.
  5. Add/adjust unit-level tests if feasible without full SSE yet.

GATE:
  - Mutation tools cannot complete side effects without going through interrupt path
    (even if resume API lands in 8X.3.3).
  - Non-mutation tools still run.
```

**Gate:** Interrupt points exist for create/update.

**Commit hint:** `feat(ai): interrupt before agent note mutations`

---

## Sub-step 8X.3.2 — SSE `approval_required`

**Goal:** Clients learn an approval is needed via the stream (or documented sync equivalent).

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.2 — Emit approval_required (or confirmed name) on agent stream.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: 8X.3.1 interrupt exists.
Read: src/ai_routes/agent.py stream loop.

TASKS:
  1. Align event naming with existing SSE JSON shapes.
  2. Emit approval_required with: tool, args summary, thread_id, resume/interrupt id.
  3. Do not parse approvals out of token text.
  4. Keep tool_start/tool_end behavior coherent (document order: interrupt vs tool_start).
  5. Update ai.md briefly if stream contract grows (append-only).

GATE:
  - Streaming client can observe approval_required without FE polish.
  - Chat stream contract unchanged.
```

**Gate:** Approval event visible on agent stream.

**Commit hint:** `feat(ai): stream approval_required for agent HITL`

---

## Sub-step 8X.3.3 — Resume by thread_id

**Goal:** Approve → resume graph → mutation proceeds; reject → no mutation.

**Prefer:** same checkpointer `thread_id` already used by agent config.

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.3 — Resume (and reject) path for HITL interrupts.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: 8X.3.1–8X.3.2 done.

TASKS:
  1. Design resume API: extend existing agent routes or add a minimal resume endpoint.
     Read OpenAPI / current agent schemas first — invent minimally.
  2. On approve: resume checkpointer thread; allow mutation to complete.
  3. On reject: end cleanly; ensure no note create/update persisted.
  4. Tenant fields remain from trusted state on resume.
  5. Document the curl/JSON body in a short comment or docs note for 8X.3.4.

GATE:
  - Approve path can complete a mutation.
  - Reject path leaves DB without that mutation.
```

**Gate:** Resume/reject semantics work via API.

**Commit hint:** `feat(ai): resume agent graph after HITL approval`

---

## Sub-step 8X.3.4 — Script smoke + tests

**Goal:** Close 8X.3 without frontend — reproducible proof.

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.4 — Curl/script smoke + tests for HITL approve/reject.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: 8X.3.3 resume works.

TASKS:
  1. Add scripts/ or docs sequence: login → agent stream → approval_required → approve → assert note exists;
     and reject path → assert note absent.
  2. Add pytest coverage for interrupt/resume/reject where practical (mock LLM if needed).
  3. Explicitly state FE approval UI is out of scope for this gate.
  4. Do not claim production-live.

GATE (8X.3 complete):
  - Script/curl proves approve and reject.
  - Automated tests cover critical path or document why remaining is manual.
  - Chat coexistence preserved; local compose healthy.
```

**Gate:** API-first HITL proven; FE not required.

**Commit hint:** `test(ai): HITL approve/reject smoke and tests`

---

## Slice 8X.3 Complete — Checklist

```
[ ] 8X.3.1 Interrupt before create/update
[ ] 8X.3.2 approval_required (or confirmed) on stream
[ ] 8X.3.3 Resume approve / reject
[ ] 8X.3.4 Script + tests; FE still out of scope
```

**Next:** Finish platform via [`slice8_X.md`](slice8_X.md) §8X.4 → [`slice-platform.md`](slice-platform.md) 7P.4–7P.8 · HITL UX later in 8X.5 / [`frontendguide.md`](../frontendguide.md)
