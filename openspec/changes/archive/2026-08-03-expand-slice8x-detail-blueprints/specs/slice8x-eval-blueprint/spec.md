## ADDED Requirements

### Requirement: Slice 8X eval detail blueprint exists
The repository MUST include `docs/documentation/blueprint/slice8_eval.md` as the executable multi-substep blueprint for the evaluation harness (Slice 8X.2). The document MUST be Cursor-ready with paste-first laws and per-substep objective prompts.

#### Scenario: Operator opens eval blueprint
- **GIVEN** this change is complete
- **WHEN** an operator opens `slice8_eval.md`
- **THEN** the file is non-empty
- **AND** it identifies itself as the detail blueprint for 8X.2 / evals
- **AND** it links back to `slice8_X.md`

### Requirement: Eval blueprint defines ordered substages
The eval blueprint MUST define ordered substages covering at least: golden schema/folder laws, retrieval and tenant-isolation cases, a runner CLI with pass/fail summary, at least five agent trajectory cases including forbid-surprise-create, and optional deterministic CI wiring with honest pass-rate documentation. Live LLM evaluation MUST NOT be required to green PR CI.

#### Scenario: Eval themes and agent minima
- **GIVEN** the eval blueprint
- **WHEN** an implementer plans the corpus
- **THEN** retrieval, tenant isolation, and ≥5 agent trajectory cases (including forbid surprise create) are required themes
- **AND** PR CI is instructed to avoid mandatory live LLM calls

### Requirement: Eval blueprint preserves tenancy and chat≠agent
Eval prompts MUST require workspace identity from JWT/trusted context only and MUST forbid replacing `/ai/chat*` with `/ai/agent*` as part of eval work.

#### Scenario: Tenant from JWT in eval law
- **GIVEN** the eval architecture law
- **WHEN** an implementer designs tenant-isolation cases
- **THEN** the blueprint states that forged workspace ids in request body/query must not expand retrieval scope beyond the JWT workspace
