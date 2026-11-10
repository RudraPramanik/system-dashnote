## ADDED Requirements

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
