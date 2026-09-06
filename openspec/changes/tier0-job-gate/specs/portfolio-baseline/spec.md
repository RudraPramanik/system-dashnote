## ADDED Requirements

### Requirement: Job-search gate tracker reflects proven evidence
`docs/documentation/blueprint/goal.md` MUST be updated when Tier 0 A/B/C/D evidence is captured so unchecked boxes do not contradict recorded smoke, FE demo, eval pass rate, or packaging artifacts. Incomplete gates MUST remain unchecked. Portfolio README live URLs MUST stay placeholders or “pending” until A/B live evidence exists.

#### Scenario: Tracker flips only with evidence
- **GIVEN** HTTPS smoke has passed and eval runner output `PASS: X/Y` is known
- **WHEN** an implementer closes the corresponding C-gate and A-gate items
- **THEN** `goal.md` marks those items complete
- **AND** the documented eval pass rate matches the runner summary

#### Scenario: Premature live links forbidden
- **GIVEN** production smoke or FE TLS demo is not yet verified
- **WHEN** README portfolio links are reviewed
- **THEN** the README MUST NOT present unverified live app/API URLs as working demos
- **AND** pending deploy language MUST remain explicit until evidence exists

### Requirement: D-gate packaging artifacts are closable
When packaging for job search, the repository MUST provide or link: README pitch with stack and architecture pointers, eval pass-rate and cost/latency fields (filled or explicitly pending with measurement method), demo video link field, GitHub topics suitable for discoverability (`rag`, `langgraph`, `fastapi`, `qdrant` or equivalent), and `docs/interview-talk-track.md` with a short pitch plus tradeoffs.

#### Scenario: Packaging checklist can be completed
- **GIVEN** A/B/C evidence is available or honestly pending
- **WHEN** an operator completes D-gate packaging
- **THEN** a stranger can open the README and find pitch, links/placeholders, metrics fields, and talk-track doc
- **AND** `goal.md` D items are updated to match what actually exists
