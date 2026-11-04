## Purpose

Defines Blueprint 9 as the operator-default AI harness-hardening path: grade targets, ordered 9H phases with Composer substages, a single trusted-context abstraction, and fallback plus error-boundary laws — as planning documents only, distinct from multi-agent Slice 9.

## Requirements

### Requirement: Blueprint 9 is the operator-default harness path
The repository MUST include a non-empty `docs/documentation/blueprint9.md` that identifies itself as the operator-default path for AI harness hardening after the product is alive. It MUST state that Blueprint 8 remains the hire and ship default, and that Blueprint 9 does not replace Tier 0, Alive, or chat-versus-agent coexistence. It MUST point to executable detail blueprints under `docs/documentation/blueprint/` for 9H substages.

#### Scenario: Operator opens Blueprint 9
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/documentation/blueprint9.md`
- **THEN** the file is non-empty
- **AND** it states that it is the default harness-hardening path to follow after Alive
- **AND** it points to detail blueprints under `docs/documentation/blueprint/` for executable substages
- **AND** it states that Blueprint 8 remains the ship and hire default

### Requirement: Phase identifiers stay distinct from Slice 9
Blueprint 9 and its detail index MUST use phase identifiers `9H.1` through `9H.6` (or equivalent `9H.*` labels). They MUST explicitly state that this path is not GraphRAG Slice 8 and not the reserved multi-agent Slice 9. The detail index MUST live at `docs/documentation/blueprint/slice9_H.md`.

#### Scenario: Operator distinguishes 9H from multi-agent Slice 9
- **GIVEN** an operator reads `blueprint9.md` or `blueprint/slice9_H.md`
- **WHEN** they look for how this path relates to Slice 9
- **THEN** they see that 9H is harness hardening
- **AND** multi-agent supervisor productization remains out of scope

### Requirement: Grade targets and locked phase order
Blueprint 9 MUST state target outcomes of security toward B+, cost control toward B+, and orchestration toward A- for this product’s notes workspace assistant. It MUST lock this calendar order, and later phases MUST NOT be prerequisites of earlier ones:

1. `9H.1` trusted tenant bind on agent tools
2. `9H.2` tool authorization aligned with existing note permissions, plus typed tool error envelopes
3. `9H.3` retrieval and tool-output injection hygiene
4. `9H.4` AI-specific request and budget limits
5. `9H.5` provider degrade modes and one harness control-plane abstraction
6. `9H.6` fixture goldens that are required before claiming those grade targets

#### Scenario: Phase order is unambiguous
- **GIVEN** the Blueprint 9 overview
- **WHEN** an implementer reads the chosen phase list
- **THEN** tenant bind appears before tool authorization and injection hygiene
- **AND** injection hygiene appears before AI budgets
- **AND** AI budgets appear before degrade-mode and control-plane polish
- **AND** grade claims are forbidden until the golden-eval phase is specified as the proof gate

### Requirement: Detail blueprints are Composer-ready and synced
The repository MUST include these non-empty detail files, each scoped to the phases named in Blueprint 9: `blueprint/slice9_trust.md` (`9H.1`), `blueprint/slice9_policy.md` (`9H.2` and `9H.3`), `blueprint/slice9_cost.md` (`9H.4`), `blueprint/slice9_resilience.md` (`9H.5`), and `blueprint/slice9_eval.md` (`9H.6`). Each phase section MUST include ordered substages, a paste-first architecture law, an objective prompt per substage (goal, constraints, validation gate), a fallback when the preferred mechanism cannot be used, and an error boundary that fails closed on tenant or authorization mistakes and fails open only where Blueprint 9 explicitly allows it for availability. Substages MUST stay consistent with the parent index: same phase order, same non-goals, and one Composer session per substep.

#### Scenario: Implementer can start one substep
- **GIVEN** an implementer opens a 9H detail blueprint
- **WHEN** they begin a single substage
- **THEN** they find an architecture law they can paste first
- **AND** they find an objective prompt with a validation gate
- **AND** the prompt forbids replacing `/ai/chat*` with `/ai/agent*` and forbids breaking the local full-stack compose path
- **AND** the substage does not require a later 9H phase to be finished first

### Requirement: Trusted context overwrites model tenant fields
Blueprint 9 MUST require that workspace id, user id, and role used by agent tools come from the authenticated request and graph session, and that model-supplied tenant fields MUST NOT override them. The `9H.1` detail blueprint MUST describe a fallback: if tool schemas must still expose those fields for the installed agent framework, the runtime overwrites them before any note or retrieval service call and never persists the model values. Missing trusted context MUST be specified as a denied tool result, not a cross-workspace call.

#### Scenario: Invented workspace is not a tool input
- **GIVEN** the 9H.1 section of the blueprint
- **WHEN** an implementer designs tool arguments
- **THEN** business arguments (query, title, content, note id) are the model’s responsibility
- **AND** workspace id, user id, and role are bound from trusted session context
- **AND** a model-invented workspace id cannot select another tenant’s notes

### Requirement: Tool authorization and typed errors stay product-shaped
The `9H.2` blueprint MUST require agent mutation and read tools to follow the same workspace role rules already used by note access (owner and admin versus member), and MUST keep human approval before create and update side effects. It MUST require tool failures to use a small stable set of error codes including at least forbidden, not found, budget exceeded, approval required, and upstream failure, returned to the model as data rather than an unhandled server error. It MUST forbid introducing a second permission product or policy engine.

#### Scenario: Member mutation still needs approval
- **GIVEN** the 9H.2 section
- **WHEN** an implementer designs create or update tool behavior
- **THEN** the tool checks role against existing note permissions
- **AND** human approval still happens before the note is written
- **AND** a denied call is a typed forbidden result, not an HTTP 500 from the agent route

### Requirement: Injection hygiene treats retrieved content as data
The `9H.3` blueprint MUST require retrieved note and file text, and tool outputs fed back into the model, to be delimited as untrusted data with an instruction that content inside those delimiters is not system instructions. It MUST require fixture cases where indexed content tries to change tenant, skip approval, or force a mutation. It MUST state that a third-party moderation vendor and automated PII redaction are out of scope for the B+ target.

#### Scenario: Poisoned note cannot retarget the tenant
- **GIVEN** the 9H.3 section
- **WHEN** an implementer plans injection tests
- **THEN** retrieved text is wrapped so the model is told it is data
- **AND** a case where note text asks to use another workspace or skip approval is a required golden theme
- **AND** buying an external content-moderation service is listed as a non-goal

### Requirement: AI budgets fail open on Redis and fail closed on quota
The `9H.4` blueprint MUST require an AI request limit per authenticated user that is stricter than the global API limit, plus a daily request budget per workspace. When provider usage metadata is present, the blueprint MUST also require a token ceiling using that metadata; when it is absent, request ceilings alone MUST be enough to claim the cost target. Exceeding a budget MUST be specified as a controlled client error (HTTP 429 or an equivalent SSE error with retry guidance), never an unhandled 500. When Redis is unavailable, the blueprint MUST require the same fail-open availability behavior as the global rate limiter, with a warning log, and MUST NOT make `/health` depend on AI budget counters.

#### Scenario: Over-budget chat is a controlled refusal
- **GIVEN** the 9H.4 section
- **WHEN** an implementer designs the over-budget path
- **THEN** the caller receives a controlled limit response with retry guidance
- **AND** the API process does not return an unhandled server error solely because the budget counter tripped

#### Scenario: Redis outage does not take down AI health
- **GIVEN** Redis errors while checking an AI budget
- **WHEN** an implementer reads the fallback
- **THEN** the request is allowed and a warning is logged
- **AND** hard health checks stay independent of AI budget keys

### Requirement: Degrade modes and one control plane
The `9H.5` blueprint MUST require one harness control plane that routes consult for policy, budget, model call, and tool execution, without a second agent framework. It MUST document degrade modes: model provider failure remains a user-safe unavailable response; missing approval persistence blocks mutations while search may continue; exhausted budget refuses further model calls for that identity. It MUST require a provider cooldown after repeated rate-limit or upstream failures so one dead provider does not stampede every request. It MUST keep existing model fallback order as the recovery path inside that cooldown.

#### Scenario: Checkpointer down blocks writes only
- **GIVEN** the 9H.5 degrade matrix
- **WHEN** approval persistence is unavailable
- **THEN** create and update tools do not commit
- **AND** search-style answers may still be served
- **AND** chat and agent routes both still exist

### Requirement: Grade claims require fixture goldens
The `9H.6` blueprint MUST require fixture (non-live-LLM) cases, suitable for pull-request CI, covering at least: model-invented workspace denied, role-forbidden tool denied, poisoned retrieved content that tries to skip approval or change tenant, and budget exceeded returning the controlled limit response. It MUST state that security B+, cost B+, and orchestration A- MUST NOT be claimed until those themes pass. Live red-team or judge suites MUST be labeled operator or nightly, not pull-request blockers.

#### Scenario: CI proof does not need live model keys
- **GIVEN** the 9H.6 section
- **WHEN** an implementer plans the gate
- **THEN** the required themes can pass with fixtures
- **AND** a live LLM key is not required to merge
- **AND** claiming the grade targets without those themes is forbidden

### Requirement: Non-goals stay explicit
Blueprint 9 MUST list as non-goals: multi-agent supervisor productization, GraphRAG or Neo4j on the small VPS, replacing `/ai/chat*` with `/ai/agent*`, a billing or payments product, a second permission engine, third-party moderation as a B+ requirement, and live model judges inside pull-request CI. Applying this change MUST be limited to writing and cross-linking these planning documents; it MUST NOT require application code changes to be complete.

#### Scenario: Apply stays documentation
- **GIVEN** this change’s blueprint set
- **WHEN** an operator checks what apply is allowed to change
- **THEN** they see documentation under `docs/documentation/` as the deliverable
- **AND** they see runtime harness work assigned to later changes sequenced by 9H substages
