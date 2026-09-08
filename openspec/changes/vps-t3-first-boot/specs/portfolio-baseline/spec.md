## ADDED Requirements

### Requirement: Trackers record HTTP first-boot without hire-ready
Job-search and platform trackers (`goal.md`, `production.md`, and related ship-path notes) MUST allow marking hosted data plane as operator-confirmed and recording HTTP-on-IP first-boot smoke. They MUST keep A7 TLS, HTTPS production smoke, frontend TLS (B7), production-live, and job-search start unchecked until HTTPS evidence exists. README MUST NOT present an HTTP IP as a stranger-ready live product URL.

#### Scenario: A1 can close without A7
- **GIVEN** the operator confirms hosted Postgres, Redis, Qdrant, and object storage are provisioned
- **WHEN** trackers are updated after this change
- **THEN** A1-style hosted-services items MAY be marked complete
- **AND** A7 TLS and hire-ready items MUST remain incomplete

#### Scenario: HTTP IP smoke is labeled first-boot
- **GIVEN** `smoke_prod.py` exited 0 against `http://<vps-public-ip>`
- **WHEN** A4-style tracker text is updated
- **THEN** the note records HTTP-on-IP first-boot PASS
- **AND** it MUST state that HTTPS prod smoke is still required

#### Scenario: README stays honest without a domain
- **GIVEN** first-boot HTTP health works and no `https://api.<domain>` exists
- **WHEN** a stranger reads the root README
- **THEN** the README does not claim a public TLS demo or production-live deploy
- **AND** any IP/HTTP mention is labeled operator first-boot, not hire-ready
