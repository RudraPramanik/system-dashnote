## Purpose

Defines the four no-secrets automated fixture themes that prove harness tenant bind, role ACL, injection hygiene, and AI budget refusal so Blueprint 9 grade claims have an executable gate.

## Requirements

### Requirement: Four harness fixture themes exist
The repository MUST include exactly four grade-proof fixture themes as automated checks that run without a live LLM provider key:

1. **Invented workspace** — a model-invented or foreign workspace id is not the identity used for NoteService / RagService; the service sees the session workspace only, or the tool is denied.
2. **Role forbidden** — a role forbidden by note permissions yields tool error code `forbidden` and MUST NOT commit a note create or update.
3. **Poisoned retrieval** — retrieved note or file text that tries to switch workspace or skip approval MUST NOT cause a cross-tenant service call and MUST NOT commit without HITL.
4. **Budget exceeded** — when the AI request budget is over ceiling, the client receives HTTP 429 or SSE `type` `error` with `code` `budget_exceeded`, and the model client MUST NOT be called for that completion.

Each theme MUST have exactly one designated executable check for the grade gate (prefer `evals/` fixture runner when the case fits; otherwise a pytest under `tests/ai/`). Duplicating the same theme as both a golden JSONL case and a separate pytest solely for the gate is forbidden. Broader regression suites outside the four designated checks MAY remain.

#### Scenario: Invented workspace theme fails closed
- **GIVEN** an agent tool path under a bound session workspace
- **WHEN** the invented-workspace fixture theme runs
- **THEN** NoteService / RagService is invoked only with the session workspace, or the tool is denied without calling another workspace
- **AND** the check completes without a live LLM API key

#### Scenario: Forbidden role theme does not commit
- **GIVEN** a note mutation the caller role is not allowed to perform
- **WHEN** the role-forbidden fixture theme runs
- **THEN** the tool outcome uses code `forbidden`
- **AND** no note create or update is committed

#### Scenario: Poisoned retrieval theme cannot retarget or skip HITL
- **GIVEN** retrieved content that instructs switching workspace or skipping approval
- **WHEN** the poisoned-retrieval fixture theme runs
- **THEN** no cross-tenant service call is made
- **AND** no mutation commits without the existing HITL approval path

#### Scenario: Over-budget theme refuses the model
- **GIVEN** the trusted user-minute or workspace-day counter is already over its ceiling
- **WHEN** the budget-exceeded fixture theme runs
- **THEN** the client contract is HTTP 429 or SSE `budget_exceeded`
- **AND** the LLM provider client is not called for that completion

### Requirement: Themes fail the run when protection is removed
Each of the four designated theme checks MUST fail the test or fixture run when the corresponding protection is absent or weakened. The happy path of pull-request CI MUST NOT `pytest.skip` (or equivalent) these themes because secrets are absent. These themes MUST NOT require a live LLM provider key, production VPS credentials, or SSH.

#### Scenario: Missing protection turns the theme red
- **GIVEN** a designated theme check and a hypothetical removal of its harness protection
- **WHEN** that check executes
- **THEN** the run exits non-zero or the assertion fails
- **AND** the failure is not hidden behind a skip conditioned on missing API keys

#### Scenario: No secrets required
- **GIVEN** pull-request CI without hosted model keys
- **WHEN** the four harness fixture themes run
- **THEN** all four execute
- **AND** none fail solely because a provider API key is unset

### Requirement: Theme proof is discoverable
Operators MUST be able to identify which file and which check is the designated executable for each of the four themes. A single documented pytest invocation (or fixture-runner invocation) MUST be able to run the four designated checks together. `/ai/chat*` and `/ai/agent*` MUST both remain. This capability MUST NOT claim security B+, cost B+, or orchestration A- by itself (grade wording is a later 9H.6 substep).

#### Scenario: Operator finds the four canonical checks
- **GIVEN** the repository after this change
- **WHEN** an operator looks for Blueprint 9 harness grade proof
- **THEN** each theme maps to one named file and check
- **AND** one documented command runs those four checks without a live LLM key

#### Scenario: Chat and agent remain separate
- **WHEN** the fixture themes are enabled
- **THEN** `/ai/chat` and `/ai/chat/stream` still exist
- **AND** `/ai/agent` and `/ai/agent/stream` still exist

### Requirement: Designated themes ride the merge-blocking PR path
The four designated harness fixture theme checks MUST execute as part of the pull-request continuous-integration test path that blocks merge (the same thin CI pytest job that already runs fixture suites without live provider keys is sufficient). Operators MUST be able to identify that path and the focused catalog command that runs the four themes together. This requirement does not itself authorize security B+, cost B+, or orchestration A- claims.

#### Scenario: Themes are on the PR pytest path
- **GIVEN** the thin PR CI workflow after this change
- **WHEN** an operator traces how harness grade proof is enforced
- **THEN** the four designated theme checks are included in the merge-blocking pytest invocation
- **AND** a documented focused command still runs those four checks together without a live LLM key

#### Scenario: Theme red fails the PR job
- **GIVEN** one designated theme assertion would fail
- **WHEN** the pull-request CI test job runs
- **THEN** the job fails
- **AND** the failure is not deferred to a non-blocking nightly lane
