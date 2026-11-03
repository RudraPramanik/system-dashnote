## ADDED Requirements

### Requirement: Local edge nginx boots without TLS certificates
The local full-stack Compose edge (`docker compose` using `docker-compose.yml`) MUST start nginx successfully when no files exist under `nginx/certs/`. Local nginx MUST proxy the documented developer edge on HTTP port 80 only and MUST NOT require an SSL certificate or key at container start. Production Compose (`docker-compose.prod.yml`) MUST continue to serve origin HTTPS on port 443 using the existing cert mount and SSL server configuration for `api.aisystem.world`.

#### Scenario: Fresh clone local edge without certs
- **GIVEN** a developer workspace with no `nginx/certs/origin.crt` or `origin.key`
- **WHEN** they run `docker compose up -d` (local full-stack file)
- **THEN** the nginx service reaches a running (not restarting) state
- **AND** `GET http://127.0.0.1/health` succeeds for hard dependencies

#### Scenario: Hosted production TLS path unchanged
- **GIVEN** production Compose with certs present under `nginx/certs/` as documented for A7
- **WHEN** operators run `docker compose -f docker-compose.prod.yml up -d` (or the deploy helpers)
- **THEN** nginx continues to listen on ports 80 and 443 with the SSL certificate paths already used for Cloudflare Full
- **AND** no change to this change requires removing or altering the production SSL server block behavior

## MODIFIED Requirements

### Requirement: Local compose remains the developer default
Changes for production platform MUST NOT break the documented local developer path: `docker compose up -d --build` followed by a successful hard health check at the documented local URL. The local nginx edge MUST stay up without TLS material so sibling frontends using `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1` can reach `/auth/*` and other API routes through port 80.

#### Scenario: Local stack still healthy after platform files land
- **GIVEN** the repository includes production compose, deploy scripts, and CI/CD workflows
- **WHEN** a developer runs the local full stack compose command
- **THEN** `GET /health` on the local edge URL succeeds for hard dependencies
- **AND** the local nginx container is not crash-looping due to missing TLS certificates

#### Scenario: Local login edge reachable after compose up
- **GIVEN** local Compose api and nginx are up via the developer path
- **WHEN** a client posts to `http://127.0.0.1/auth/login` (valid or invalid credentials)
- **THEN** the request reaches the API through nginx (HTTP status from the application, not a browser connection refused to port 80)
