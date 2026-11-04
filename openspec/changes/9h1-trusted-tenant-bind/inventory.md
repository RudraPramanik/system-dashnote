# 9H.1.1 — Tenant field inventory (pre-bind)

No runtime changes in this note. Source snapshot before 9H.1.2.

## Tool schemas (`src/ai/tools/schemas.py`)

| Tool schema | Tenant fields (model-supplied) | Business fields |
|-------------|--------------------------------|-----------------|
| `SearchNotesArgs` | `workspace_id`, `user_id`, `role` | `question` |
| `CreateNoteArgs` | `workspace_id`, `user_id`, `role` | `title`, `content` |
| `UpdateNoteArgs` | `workspace_id`, `user_id`, `role` | `note_id`, `content` |
| `SummarizeWorkspaceArgs` | `workspace_id`, `user_id`, `role` | _(none)_ |

Field descriptions all say: “from agent state — do not modify.”

## Tool wrappers (`src/ai/tools/note_tools.py`)

| Tool | Signature takes tenant? | Docstring / description asks model to pass tenant? |
|------|-------------------------|-----------------------------------------------------|
| `search_notes` | yes | docstring + StructuredTool description |
| `create_note` | yes (also copied into HITL `approval_args`) | docstring + description |
| `update_note` | yes (also HITL `approval_args`) | docstring + description |
| `summarize_workspace` | yes | description |

## System prompt (`src/ai/workflows/workspace_assistant.py`)

| Location | Text |
|----------|------|
| `WORKSPACE_ASSISTANT_PROMPT` rule 1 | “ALWAYS pass workspace_id, user_id, and role exactly as they appear in your system context…” |
| `call_model` injected block | Prints `workspace_id` / `user_id` / `role` from graph state + “Always use these exact values in every tool call.” |

## Callers / fixtures that pass tenant tool args (task 1.2)

| Location | Notes |
|----------|--------|
| `tests/ai/test_agent_hitl.py` | Local `_CreateArgs` + tool_calls include tenant fields (standalone mock graph, not production schemas) |
| `evals/fixtures/traj-*.json` | Tool **names** only (`search_notes`, etc.) — no tenant arg payloads |
| `evals/golden/tenant_isolation.jsonl` | HTTP forged-workspace probe for `/ai/test-search` — not agent tool schemas |
| No production script found that POSTs agent tool args with `workspace_id` | Product UI must not send tenant on resume/reject (already specified) |

**Bind implication:** Prefer dropping tenant fields from production schemas; update HITL unit mock if needed; traj fixtures need no arg changes.

## 9H.1.4 fixture note

Eval traj fixtures (`evals/fixtures/traj-*.json`) only list tool names — they cannot assert service kwargs without a live agent trajectory runner + provider key. The unit suite `tests/ai/test_harness_trust.py` covers the invented-workspace / harness-bind theme for CI.
