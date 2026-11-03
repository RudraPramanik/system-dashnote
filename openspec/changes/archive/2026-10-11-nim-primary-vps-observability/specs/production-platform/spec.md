## ADDED Requirements

### Requirement: Hosted AI env includes Langfuse and model lines
The committed production env template and the operator runbook MUST name `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and either `LANGFUSE_HOST` or `LANGFUSE_BASE_URL`, plus `LLM_MODEL` and `LLM_MODEL_FALLBACKS`, as optional-but-recommended VPS `.env` entries for hosted AI. Filled values MUST remain in the gitignored VPS `.env` only. After those values change on the host, operators MUST recreate the `api` and `worker` containers (not only restart) so the Langfuse client and in-process LLM cache reload. Soft `GET /health/ai` MUST remain non-blocking for hard deploy smoke. Live AWS IAM access keys MUST NOT be committed under `infra/tf.env` or any other tracked path.

#### Scenario: Template names Langfuse and model vars
- **GIVEN** an operator opens `.env.production.example`
- **WHEN** they look for AI observability and model settings
- **THEN** they see Langfuse key and host/base-url placeholders
- **AND** they see `LLM_MODEL` and `LLM_MODEL_FALLBACKS` placeholders or documented defaults
- **AND** no live secret values appear in that file

#### Scenario: Recreate after env change
- **GIVEN** the VPS `.env` gained Langfuse keys or new model lines
- **WHEN** the operator follows the runbook to apply them
- **THEN** `api` and `worker` are recreated so the new env is loaded
- **AND** `GET /health/ai` can report Langfuse enabled and the configured model without failing `GET /health`

#### Scenario: IAM keys stay out of git
- **GIVEN** an operator manages AWS credentials for the edge instance
- **WHEN** they store access keys
- **THEN** those keys MUST NOT be committed into the repository
- **AND** `infra/tf.env` MUST NOT contain live access-key material
