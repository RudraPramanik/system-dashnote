## ADDED Requirements

### Requirement: Integrations surfaces for the client
The frontend guide MUST document inbound/integrations routes a Next.js client may call: authenticated WhatsApp link start/confirm/unlink under `/integrations/whatsapp/link*`, and a pointer to inbound email as a provider/n8n webhook (`POST /integrations/inbound/email`) that uses the inbound API key (and optional HMAC), not the user JWT. The guide MUST NOT instruct the browser to send a client-chosen `workspace_id` to override tenancy on those JWT-scoped link routes. Deep provider setup MAY be linked to `docs/inbound-channels.md` instead of copied in full.

#### Scenario: WhatsApp link appears in the domain map
- **WHEN** a frontend adds a “link WhatsApp” setting
- **THEN** the guide MUST list `POST /integrations/whatsapp/link/start`, `POST /integrations/whatsapp/link/confirm`, and `DELETE /integrations/whatsapp/link`
- **AND** MUST state those calls use `Authorization: Bearer <access_token>`

#### Scenario: Inbound email is not a user-session upload
- **WHEN** a frontend author looks for “email ingest”
- **THEN** the guide MUST state inbound email is a signed provider webhook, not a logged-in user multipart upload
- **AND** MUST NOT tell the Next.js app to call it with only the user JWT as the inbound secret

### Requirement: Operational health includes the soft AI probe
The frontend guide MUST document `GET /health` as the hard API/DB/Redis check and `GET /health/ai` as an optional soft Qdrant/LLM probe. UI MAY use `/health/ai` to explain degraded AI; it MUST NOT treat `/health/ai` failure as equivalent to the whole API being down.

#### Scenario: Health table lists both probes
- **WHEN** a frontend implements a status or “AI unavailable” banner
- **THEN** the guide MUST mention `GET /health` and `GET /health/ai`
- **AND** MUST distinguish hard unavailability from soft AI degradation

### Requirement: Diagnostic search uses the mounted GET contract
The frontend guide MUST document engineering/diagnostic search as `GET /ai/test-search` with query parameters `q` and optional `limit`. It MUST NOT present `POST /ai/test-search` as the live product or diagnostic contract. Workspace isolation MUST remain JWT-only (`wid`); clients MUST NOT send `workspace_id` on this route.

#### Scenario: Guide agrees with itself on test-search
- **WHEN** a frontend or agent follows the AI domain map and the quick-reference section
- **THEN** both MUST describe `GET /ai/test-search`
- **AND** MUST NOT leave a contradictory `POST /ai/test-search` as the primary documented method
