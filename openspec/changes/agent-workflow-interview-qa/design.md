## Context

`qs2.md` is the production RAG/AI interview gate (with mermaid). `qs3.md` is empty. See `proposal.md` for why; see `specs/agent-workflow-interview-qa/spec.md` for the coverage contract.

This change is documentation only. Match `qs2.md` format. Do not rewrite RAG, embeddings, vector DBs, enterprise SQL-vs-vectors, TTFT/E2E, or tenant-filter-from-JWT — **link to `qs2.md`**.

Assumption recorded: the “five core patterns” are the production **workflow** patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer). Agent primitives (tools, plan-execute, reflection, multi-agent) sit beside them, not instead of them.

## Goals / Non-Goals

**Goals:**

- One long `qs3.md` that is an interview script + concept gate for agents, workflows, and automations.
- Locked TOC so apply fills every spec scenario, with a mermaid at each major section.
- Explicit “Already in qs2” pointers so apply does not paste RAG essays.

**Non-Goals:**

- Rewriting `qs2.md` beyond a short pointer to `qs3.md`.
- Implementing agents, HITL, MCP servers, or Temporal in code.
- Splitting into multiple files.

## Decisions

### D1. Same study model as qs2

**Choice:** Title, purpose, TOC, diagram index, `### Question`, **Spoken** / **If they probe**, mermaid after each `##` heading. **Example (DashNoteSystem):** only when it illustrates (LangGraph tools, ARQ, chat≠agent).

**Why:** User asked for the same model. Consistency beats a new format.

**Alternatives considered:** Short pattern cheat-sheet (fails concept gate). Academic survey with paper names only (fails “how would you ship it?”).

### D2. qs2 exclusion map (do not rewrite)

| Topic | Point to |
|-------|----------|
| Tokens, context window, embeddings, chunking | qs2 §1–2 |
| RAG pipeline, enterprise RAG-on-DB, hybrid/rerank | qs2 §3–5 |
| Vector DBs, index sync, embed lag | qs2 §6–7 |
| Chat vs agent *as product surfaces* | qs2 §8 |
| TTFT vs E2E, caching layers, model routing cost | qs2 §10–11 |
| Tenant filters from identity, prompt injection basics | qs2 §12 |
| RAG goldens, empty retrieval, provider 503 | qs2 §13, §15 |
| Thread vs RAG vs checkpoint (intro) | qs2 §17 |

**qs3 adds instead:** retrieval *as a tool*, trajectory evals, graph interrupts, compaction, parallel tools, durable jobs, MCP, sandboxes, multi-agent, the five workflow patterns in depth.

### D3. Locked TOC

| # | Section | Must include |
|---|---------|----------------|
| 0 | How to use | Three-file map (qs / qs2 / qs3); format; length; diagram note |
| 1 | Workflow vs agent | Compiled pipeline vs autonomous loop; default to workflow |
| 2 | Five core patterns (overview) | Name all five; when each wins; one summary diagram |
| 3 | Prompt chaining | Sequential LLM steps; error propagation |
| 4 | Routing | Classifier/router to specialist paths |
| 5 | Parallelization | Fan-out/fan-in; sectioning vs voting |
| 6 | Orchestrator-workers | Planner delegates to workers |
| 7 | Evaluator-optimizer | Critique-revise loop with cap |
| 8 | Tool use / function calling | Schemas, parallel calls, validation, identity, idempotency |
| 9 | Plan and execute | Plan-then-act, ReWOO vs ReAct; replanning |
| 10 | Reflection | Reflexion / self-critique; stop conditions |
| 11 | Control loops compared | ReAct vs graph vs plan-execute vs reflection |
| 12 | Orchestration & durable automation | Graphs, queues, Temporal-style durable exec; LLM inside a job |
| 13 | HITL, interrupts, approvals | Deeper than qs2: resume, expiry, replay |
| 14 | Memory for long agent runs | Compaction, scratchpads, working vs episodic; pointer to qs2 §17 |
| 15 | Multi-agent | Supervisor, handoff, swarm; when *not* to |
| 16 | MCP, sandboxes, computer use | Tool servers, code exec isolation, browser agents (high level) |
| 17 | Agent evals & tracing | Trajectories, tool-correctness; pointer to qs2 RAG evals |
| 18 | Security & blast radius for tools | Pointer to qs2 §12; add tool IAM, injection via tool output |
| 19 | Whiteboard: production automation | Event → workflow → HITL → side effect |
| 20 | Counter-questions | Workflow vs agent; ReAct vs graph; multi-agent vs one agent+tools |

Also appear somewhere: deterministic vs LLM steps; background vs interactive; when not to use an agent; skills/playbooks; error recovery / compensating actions.

### D4. Cross-links

**Choice:** Header pointers in `qs3.md` to `qs2.md` and `qs.md`. Add one line in `qs2.md` header pointing to `qs3.md`. If `qs.md` already points at `qs2.md`, add `qs3.md` there too.

### D5. Diagrams

**Choice:** Mermaid after each `##` section (five patterns each get their own diagram in §3–§7). Whiteboard §19 gets a four-box automation picture (event, workflow, HITL, system of record).

## Risks / Trade-offs

- **[Risk] Duplicating qs2 §8–9** → Mitigation: D2 exclusion map; qs3 talks *patterns and control loops*, not “we have /ai/chat and /ai/agent.”
- **[Risk] Turning into a paper dump (ReAct, Reflexion, ReWOO)** → Mitigation: Each named loop gets a production “when I ship this” answer, not a citation list.
- **[Risk] Five patterns vs “tool, plan, reflect, multi-agent, memory” as the five** → Mitigation: D3 uses Anthropic-style workflows as *the five*; primitives get their own sections. Intro states that naming choice in one sentence.
- **[Trade-off] Long file** → Same as qs2; TOC + diagram index.

## Migration Plan

1. Author `qs3.md` to D3.
2. Pointers in `qs2.md` / `qs.md`.
3. Rollback: delete `qs3.md` content; revert pointers.

## Open Questions

None. Pattern naming is decided in D3.
