# Slice 8X.3 — HITL API-First (Agent Mutations)
## Final Cursor Prompts (4 Sub-steps, Raise Autonomy Safely, No FE Required)

> **Parent index:** [`slice8_X.md`](slice8_X.md)  
> **Sequence (chosen / deploy-first):** After **8X.2** evals (and after **7P.8**) per [`slice8_X.md`](slice8_X.md) — do not start before VPS smoke on the chosen path.  
> **Code anchors:** `src/ai_routes/agent.py` · `src/ai/workflows/workspace_assistant.py` · `src/ai/tools/note_tools.py` · `src/ai/memory/checkpointer.py` · [`ai.md`](../ai.md) Slice 6  
> **When to run:** After **8X.2** agent trajectory thinking (recommended); 8X.1 CI recommended.  
> **Goal:** Human approval before `create_note` / `update_note` side effects — API + SSE + script/tests. **No** polished Next.js console for this gate.  
> **Pending state:** LangGraph checkpointer + `thread_id` (not a new `pending_actions` table; not Slice 7 automation queue).

---

## Slice Overview

```
8X.3.1  Interrupt          before create/update; LangGraph API version check first
8X.3.2  SSE event          locked approval_required JSON; emit then close stream
8X.3.3  Resume             thread_id + workspace ownership validation; approve/reject
8X.3.4  Smoke + tests      curl/script under new contract; FE still forbidden
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
| Installed LangGraph | Known version (see `requirements/base.txt`) | Read installed API before interrupt code |
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
  On resume/reject: re-validate that thread_id (checkpoint) belongs to the
  authenticated caller’s workspace BEFORE any mutation. Arbitrary thread_id → deny.

CHECKPOINTER = PENDING STATE:
  Reuse existing LangGraph checkpointer + thread_id for interrupt/resume.
  Do NOT invent a second persistence system for this gate.
  Do NOT require a new pending_actions table for 8X.3.
  Slice 7 AutomationDecisionEngine / automation review queue is a DIFFERENT surface —
  do not conflate it as a mandatory dependency for agent mutation HITL.
  Checkpointer ≠ product AIThread ORM tables (laws in ai.md).

LANGGRAPH API DISCIPLINE:
  requirements may say langgraph>=0.1.0 — too loose to assume one interrupt style.
  BEFORE coding: read installed LangGraph version + existing graph code;
  use that version’s interrupt API (e.g. interrupt() vs legacy NodeInterrupt).
  When implementing, prefer tightening the pin to the API actually used.

SSE / STREAM CONTRACT (locked):
  Existing events (verify in ai_routes/agent.py):
    token | tool_start | tool_end | done | error  (+ trailing [DONE] today)
  New event shape (locked keys — extend only with docs):
    {
      "type": "approval_required",
      "tool": "<tool_name>",
      "args": { ... },          // or args summary object — document which
      "thread_id": "<id>",
      "interrupt_id": "<id>"    // resume/interrupt identity
    }
  If naming must change to fit taxonomy, document the FINAL name and keep the same fields.

SSE LIFECYCLE (preferred default):
  Emit approval_required → then END the SSE stream (same spirit as done+[DONE]).
  Client calls resume/reject API with same thread_id (reconnect) — do not keep
  the stream open waiting for approval (proxy/timeout pain).
  Document ordering vs tool_start/tool_end (e.g. interrupt before side effect;
  may appear after tool_start if tool began but before NoteService commit).

FE OUT OF SCOPE:
  Polished Next.js approval UI is NOT required for 8X.3 gate.
  Script/curl (+ tests) are enough.

SCOPE:
  Do NOT treat docs/documentation/blueprint/new.md as source of truth.

FALLBACK:
  If LangGraph interrupt APIs differ from assumptions → read installed version; invent minimally.
  If resume cannot share thread_id → STOP and report; do not silently drop mutations
  without user-visible control.
```

---

## Fallbacks / out of scope

| Out of scope | Defer to |
|--------------|----------|
| Next.js approval console | 8X.5 / `frontendguide.md` B5 |
| Multi-agent / supervisor | Slice 9 |
| Automation worker approval queue (7A) | Different surface — not required for 8X.3 |
| New `pending_actions` table for agent HITL | Forbidden for this gate — use checkpointer |
| Replacing chat with agent | Never |
| Claiming production-live | 7P.8 smoke |

**Locked stream contract:**

```
Existing:  token | tool_start | tool_end | done | error
Add:       approval_required { type, tool, args, thread_id, interrupt_id }
Lifecycle: emit approval_required → close SSE → client resume/reject API
Approve:   ownership-checked resume → mutation may complete
Reject:    end turn; no mutation side effect
```

---

## Sub-step 8X.3.1 — Interrupt before mutations

**Goal:** Graph pauses before `create_note` / `update_note` (or equivalent) commits side effects.

**Read first:** installed LangGraph version, `workspace_assistant.py`, `note_tools.py`, interrupt docs for that version.

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.1 — Interrupt before agent note mutation side effects.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: readiness gate passed; read agent graph + tools + installed LangGraph.

TASKS:
  1. Record installed LangGraph version; choose the correct interrupt API for it.
     Note that langgraph>=0.1.0 is too loose — plan to tighten pin when this lands.
  2. Identify create/update tool execution path in the graph ToolNode / wrappers.
  3. Add interrupt (or equivalent) BEFORE NoteService create/update side effects.
     Persist pending interrupt via existing checkpointer — no new pending_actions table.
  4. Ensure search/summarize tools are not blocked by mutation HITL.
  5. Keep chat routes and RagService chat path untouched.
  6. Add/adjust unit-level tests if feasible without full SSE yet.

GATE:
  - Mutation tools cannot complete side effects without going through interrupt path
    (even if resume API lands in 8X.3.3).
  - Non-mutation tools still run.
  - Interrupt API choice is version-grounded.
```

**Gate:** Interrupt points exist for create/update.

**Commit hint:** `feat(ai): interrupt before agent note mutations`

---

## Sub-step 8X.3.2 — SSE `approval_required`

**Goal:** Clients learn an approval is needed via the stream; lifecycle and JSON shape are locked.

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.2 — Emit approval_required on agent stream with locked contract.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: 8X.3.1 interrupt exists.
Read: src/ai_routes/agent.py stream loop (token, tool_start, tool_end, done, error).

TASKS:
  1. Emit approval_required with locked fields:
     type, tool, args (or documented args summary), thread_id, interrupt_id.
  2. After emitting approval_required, END the SSE stream (preferred lifecycle).
     Do not leave the connection open waiting for approval.
  3. Do not parse approvals out of token text.
  4. Document ordering vs tool_start/tool_end (interrupt before NoteService side effect).
  5. Update ai.md briefly if stream contract grows (append-only).

GATE:
  - Streaming client can parse approval_required without guessing keys.
  - Client knows to reconnect / call resume after stream ends.
  - Chat stream contract unchanged.
```

**Gate:** Approval event visible; lifecycle explicit.

**Commit hint:** `feat(ai): stream approval_required for agent HITL`

---

## Sub-step 8X.3.3 — Resume by thread_id

**Goal:** Approve → ownership check → resume graph → mutation proceeds; reject → no mutation.

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
  2. MANDATORY: before resume/reject side effects, verify thread_id (checkpoint)
     belongs to the authenticated caller’s workspace. Cross-tenant thread_id → deny.
  3. On approve: resume checkpointer thread; allow mutation to complete.
  4. On reject: end cleanly; ensure no note create/update persisted.
  5. Tenant fields remain from trusted auth/graph state — never from model args.
  6. Document the curl/JSON body in a short comment or docs note for 8X.3.4.

GATE:
  - Approve path can complete a mutation after ownership check.
  - Reject path leaves DB without that mutation.
  - Cross-workspace thread_id cannot resume.
```

**Gate:** Resume/reject semantics work via API with tenant ownership validation.

**Commit hint:** `feat(ai): resume agent graph after HITL approval`

---

## Sub-step 8X.3.4 — Script smoke + tests

**Goal:** Close 8X.3 without frontend — reproducible proof under the locked contract.

---

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 8X.3.4 — Curl/script smoke + tests for HITL approve/reject.

Paste ARCHITECTURE LAW — Slice 8X.3 HITL first.
Prerequisite: 8X.3.3 resume works.

TASKS:
  1. Add scripts/ or docs sequence under the locked contract:
     login → agent stream → parse approval_required → stream ends →
     approve (same thread_id) → assert note exists;
     and reject path → assert note absent.
  2. Include at least one negative check or documented test: wrong-workspace thread_id denied.
  3. Add pytest coverage for interrupt/resume/reject where practical (mock LLM if needed).
  4. Explicitly state FE approval UI is out of scope for this gate.
  5. Do not claim production-live.

GATE (8X.3 complete):
  - Script/curl proves approve and reject with emit-then-close + resume.
  - Ownership validation is exercised or explicitly tested.
  - Automated tests cover critical path or document why remaining is manual.
  - Chat coexistence preserved; local compose healthy.
```

**Gate:** API-first HITL proven; FE not required.

**Commit hint:** `test(ai): HITL approve/reject smoke and tests`

---

## Slice 8X.3 Complete — Checklist

```
[ ] 8X.3.1 Interrupt before create/update (version-grounded API; checkpointer only)
[ ] 8X.3.2 approval_required locked JSON + emit-then-close SSE
[ ] 8X.3.3 Resume approve / reject with workspace ownership check
[ ] 8X.3.4 Script + tests under new contract; FE still out of scope
```

**Next (chosen / deploy-first):** HITL UX in 8X.5 / [`frontendguide.md`](../frontendguide.md) if needed · Parent: [`slice8_X.md`](slice8_X.md) (platform + FE + evals should already be done)
