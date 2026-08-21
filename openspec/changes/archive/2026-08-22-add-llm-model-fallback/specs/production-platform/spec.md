## MODIFIED Requirements

### Requirement: Soft AI health does not block hard health
`GET /health` MUST continue to treat Postgres and Redis as hard dependencies and MUST NOT fail solely because Qdrant or LLM providers are unavailable. The system MUST provide `GET /health/ai` that reports AI/Qdrant readiness as soft status (reachable, degraded, or not configured) **and** a soft LLM dependency (reachable, degraded, or not configured). `GET /health/ai` MUST NOT be required for the deploy smoke hard gate unless an operator explicitly opts into soft checks. Soft Qdrant or LLM probe failures MUST NOT crash the API process.

#### Scenario: API up while Qdrant is down
- **GIVEN** Postgres and Redis are reachable and Qdrant is unreachable
- **WHEN** a client calls `GET /health`
- **THEN** the response reflects hard-dependency health without requiring Qdrant success

#### Scenario: Soft AI health endpoint reports Qdrant separately
- **GIVEN** the API is running with `QDRANT_URL` configured
- **WHEN** a client calls `GET /health/ai`
- **THEN** the response reports Qdrant readiness as soft status
- **AND** a Qdrant outage does not change the hard success criteria of `GET /health`

#### Scenario: Soft AI health when Qdrant is not configured
- **GIVEN** the API is running without `QDRANT_URL`
- **WHEN** a client calls `GET /health/ai`
- **THEN** the response indicates AI/Qdrant is not configured (soft)
- **AND** `GET /health` remains independent of that result

#### Scenario: Soft AI health reports LLM separately
- **GIVEN** the API is running with at least one LLM candidate configured
- **WHEN** a client calls `GET /health/ai`
- **THEN** the response includes a soft LLM dependency status
- **AND** a retired or unreachable LLM does not change the hard success criteria of `GET /health`
