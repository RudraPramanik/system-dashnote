## ADDED Requirements

### Requirement: Redis-backed rate limiting fails open on Redis errors
When Redis is configured and application rate limiting is enabled, a Redis command failure used for rate-limit counters (including connection errors, timeouts, and provider quota / "rate-limited" responses) MUST NOT produce an unhandled server error. The limiter MUST fail open for that request (allow the request to proceed without applying the counter) OR return a controlled non-5xx degradation only where an existing authenticated contract already requires a specific status — default for the global limiter is fail open. Hard health probing MUST remain able to reach the `/health` handler logic without being converted into HTTP 500 solely by a Redis rate-limit dependency failure.

#### Scenario: Global limiter Redis error does not 500
- **GIVEN** Redis is configured and the global rate limiter is active
- **AND** the Redis counter command fails with a provider quota or connection error
- **WHEN** a client calls any route that uses the global limiter, including `GET /health`
- **THEN** the response is not an unhandled Internal Server Error caused by that Redis error
- **AND** the request is allowed to continue (fail open) so hard health can still report database/redis readiness

#### Scenario: Successful Redis counters still enforce limits
- **GIVEN** Redis counter commands succeed
- **WHEN** a client exceeds the configured window limit for a scope
- **THEN** the API still returns HTTP 429 with Retry-After as today

### Requirement: Production Redis cutover prefers Redis Cloud for cache and ARQ
Operators recovering hosted production MUST point both `REDIS_URL` and `ARQ_REDIS_URL` at a Redis-protocol endpoint that supports blocking list pops for ARQ. The documented recovery default MUST be Redis Cloud (Essentials free or paid) for both URLs on the same database when only one free database is available. Layerbase Free MUST NOT be documented as the production always-on ARQ or sole cache host while Docker healthchecks and the worker hold continuous connections, because free hibernation and mandatory idle sleep conflict with that topology. Momento and Vercel KV MUST NOT be documented as ARQ backends. Secrets MUST stay in the VPS `.env` (and optional local operator `.env`); example files MUST show URL shapes only.

#### Scenario: Operator follows Redis Cloud cutover
- **GIVEN** Redis Cloud credentials are available as a Redis DSN
- **WHEN** the operator updates the VPS `.env`
- **THEN** both `REDIS_URL` and `ARQ_REDIS_URL` use that Redis Cloud endpoint (TLS as required by the provider)
- **AND** documentation warns about free-tier connection and ops/sec caps
- **AND** no secret values are committed to git

#### Scenario: Layerbase free is deferred for always-on production
- **GIVEN** Layerbase Free hibernates after idle time and requires weekly sleep share
- **WHEN** an operator reads the recovery / Redis section of the runbook or system docs
- **THEN** Layerbase Free is listed as unsuitable for the always-on worker + 30s healthcheck path
- **AND** Solo/always-on Layerbase MAY be noted as a future paid option, not the default cutover

### Requirement: Hosted Redis storm stop precedes cutover
Before pointing production at a new Redis provider, operators MUST stop the ARQ worker restart storm (and SHOULD avoid continuous failing health probes against a refused Redis) so the new database is not immediately exhausted. After env update, operators MUST recreate or restart `api` and `worker`, then verify Redis reachability via hard health once Postgres is also healthy. Existing Compose healthcheck interval MAY remain; no separate keep-alive cadence is required for Redis Cloud beyond normal `/health` traffic.

#### Scenario: Cutover order
- **GIVEN** the worker has been crash-looping against a refused Redis
- **WHEN** the operator performs recovery
- **THEN** the worker is stopped before the new Redis URL is put under load by restarts
- **AND** after `.env` update, `api` and `worker` are restarted against the new URLs
- **AND** docs do not require an extra sub-minute keep-alive solely to defeat a Redis Cloud "14 day inactive" rule — normal health traffic is enough while the stack is up
