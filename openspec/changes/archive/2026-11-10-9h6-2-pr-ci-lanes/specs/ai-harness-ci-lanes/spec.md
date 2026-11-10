## Purpose

Defines the Blueprint 9 operator-visible split between merge-blocking pull-request harness proof and non-blocking operator/nightly live red-team or LLM-as-judge work.

## ADDED Requirements

### Requirement: Harness proof blocks merge on the PR lane
The four Blueprint 9 harness fixture themes MUST run on the pull-request continuous-integration path that gates merge. Failure of any designated theme check MUST fail that PR check. The PR lane MUST NOT require a live LLM provider key, production VPS credentials, or SSH to execute those themes.

#### Scenario: Theme failure blocks the PR check
- **GIVEN** a pull request that breaks one designated harness fixture theme
- **WHEN** thin PR CI runs its test job
- **THEN** the job exits non-zero
- **AND** the failure is not hidden behind a skip for missing provider secrets

#### Scenario: PR lane needs no live provider keys
- **GIVEN** pull-request CI without hosted model keys
- **WHEN** the harness fixture themes execute on that path
- **THEN** all four themes run
- **AND** none fail solely because a provider API key is unset

### Requirement: Live red-team and judges stay off the merge gate
Live jailbreak suites, live-mode eval runs that call a real model or stack, and LLM-as-judge suites MUST be labeled operator or nightly only. Those lanes MUST NOT be required for merge. Documentation that mentions them MUST state they are non-blocking. PR CI MUST NOT gain provider API keys solely to run those suites.

#### Scenario: Operator sees non-blocking nightly label
- **GIVEN** operator docs or workflow comments that mention live jailbreak, live eval mode, or LLM-as-judge
- **WHEN** an operator reads the lane guidance for Blueprint 9 harness proof
- **THEN** those suites are labeled operator or nightly only
- **AND** they are stated as non-blocking for merge

#### Scenario: No live keys added to PR for judges
- **GIVEN** the thin PR CI workflow
- **WHEN** an operator inspects required secrets and steps for a green harness proof
- **THEN** no live LLM provider key is required for the merge-blocking harness themes
- **AND** no new merge-required job exists whose green result depends on a live judge or jailbreak suite

### Requirement: Chat and agent remain while lanes are documented
Documenting or wiring the PR-versus-nightly split MUST NOT collapse `/ai/chat*` into `/ai/agent*`. Both surfaces MUST remain. This capability MUST NOT claim security B+, cost B+, or orchestration A- by itself.

#### Scenario: Surfaces stay separate after lane docs
- **WHEN** the PR-versus-nightly lane documentation is in place
- **THEN** `/ai/chat` and `/ai/chat/stream` still exist
- **AND** `/ai/agent` and `/ai/agent/stream` still exist
