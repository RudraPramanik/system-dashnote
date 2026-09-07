## Why

`qs2.md` covers production RAG and only sketches agents (chat vs agent, a capped loop, HITL). Hire loops for agent/automation roles ask for workflow patterns, plan-execute, reflection, tool/function calling, orchestration, multi-agent, and durable jobs — topics `qs2.md` does not teach. Candidates need a third interview gate at `qs3.md` that goes deep on agents and workflows and **points back** to `qs2.md` instead of repeating RAG, tenancy, latency SLOs, or embedding theory.

## What Changes

- Author a comprehensive interview Q&A at `docs/documentation/qs3.md` for production AI **agents, workflows, and automations**.
- Cover the **five core workflow patterns** (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) plus fundamentals: tool/function calling, plan-and-execute, reflection, orchestration, memory for agents, multi-agent, durable/background automation, and agent evals.
- Match the `qs2.md` study model: Spoken / If they probe, mermaid diagrams, length allowed, labeled DashNoteSystem examples only.
- **Do not duplicate** `qs2.md`. Where RAG, tenancy filters, TTFT/E2E, golden RAG evals, or chat-vs-agent coexistence are needed, **reference** `qs2.md` sections.
- Light cross-links from `qs2.md` (and `qs.md` if it already lists `qs2.md`) so readers can find the agent track.
- No application code, API, or runtime behavior changes.

## Capabilities

### New Capabilities

- `agent-workflow-interview-qa`: Production-level AI agent, workflow, and automation interview Q&A at `docs/documentation/qs3.md` — five workflow patterns, plan/reflect/tools/orchestration, and related hire-loop topics not covered in `qs2.md`.

### Modified Capabilities

- (none — `ai-engineering-interview-qa` is not yet a main spec; cross-links from `qs2.md` are owned by this new capability)

## Impact

- **Docs:** Primary deliverable `docs/documentation/qs3.md`. Pointers from `qs2.md` (and optionally `qs.md`).
- **Consumers:** Agent/automation interviews, system-design rounds, and concept-clearance for production workflows vs autonomous agents.
- **APIs / code:** None.
- **Non-goals:** Implementing agents, HITL, LangGraph changes, RPA products, or rewriting `qs2.md` / `qs.md`.
