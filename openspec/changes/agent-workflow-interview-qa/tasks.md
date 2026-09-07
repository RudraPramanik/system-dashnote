## 1. Scaffold qs3.md

- [x] 1.1 Write `docs/documentation/qs3.md` header: title, three-file map (`qs.md` / `qs2.md` / `qs3.md`), Spoken / If they probe format, length expected, mermaid note, and the naming choice that the five core patterns are workflow patterns
- [x] 1.2 Add table of contents matching design.md D3 sections 0–20 and a diagram index

## 2. Workflow vs agent and the five patterns

- [x] 2.1 Write §1 workflow vs agent Q&A (compiled pipeline vs autonomous loop; default to workflow) with mermaid; point to qs2 §8 for product chat-vs-agent surfaces
- [x] 2.2 Write §2 five-pattern overview Q&A plus a summary mermaid of all five
- [x] 2.3 Write §3 prompt chaining Q&A + mermaid (sequential steps, error propagation)
- [x] 2.4 Write §4 routing Q&A + mermaid
- [x] 2.5 Write §5 parallelization Q&A + mermaid (sectioning vs voting)
- [x] 2.6 Write §6 orchestrator-workers Q&A + mermaid
- [x] 2.7 Write §7 evaluator-optimizer Q&A + mermaid (critique-revise with cap)

## 3. Tools, plan, reflection, control loops

- [x] 3.1 Write §8 tool use / function calling Q&A + mermaid (schemas, parallel calls, validation, identity-scoped execution, idempotency, blast radius)
- [x] 3.2 Write §9 plan-and-execute Q&A + mermaid (plan-then-act, ReWOO vs ReAct, replanning)
- [x] 3.3 Write §10 reflection Q&A + mermaid (critique with stop condition)
- [x] 3.4 Write §11 control-loop comparison Q&A + mermaid (ReAct vs graph vs plan-execute vs reflection)

## 4. Production automation and remaining depth

- [x] 4.1 Write §12 orchestration and durable automation Q&A + mermaid (graphs, queues, durable exec, LLM inside a job, background vs interactive, deterministic vs LLM steps)
- [x] 4.2 Write §13 HITL / interrupts / approvals Q&A + mermaid (resume, expiry, replay); do not rewrite qs2 HITL intro
- [x] 4.3 Write §14 long-run memory Q&A + mermaid (compaction, scratchpads); pointer to qs2 §17
- [x] 4.4 Write §15 multi-agent Q&A + mermaid (supervisor, handoff; when not to)
- [x] 4.5 Write §16 MCP, sandboxes, computer use Q&A + mermaid
- [x] 4.6 Write §17 agent evals and tracing Q&A + mermaid (trajectories, tool-correctness); pointer to qs2 RAG evals
- [x] 4.7 Write §18 tool security / blast radius Q&A + mermaid; pointer to qs2 §12
- [x] 4.8 Write §19 production-automation whiteboard Q&A + mermaid (event → workflow → HITL → side effect)
- [x] 4.9 Write §20 counter-questions covering at least workflow vs agent, ReAct vs graph, and multi-agent vs one agent with tools

## 5. Cross-links and coverage check

- [x] 5.1 Add a short `qs2.md` header pointer to `qs3.md`; if `qs.md` already points at `qs2.md`, add `qs3.md` there too
- [x] 5.2 Label DashNoteSystem illustrations as **Example (DashNoteSystem):**; keep answers vendor-neutral; do not duplicate qs2 D2 exclusion-map topics
- [x] 5.3 Walk spec scenarios and design D3 must-include list (including skills/playbooks, compensating actions, when not to use an agent); fill gaps before apply is complete
