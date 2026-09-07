## Purpose

Production-safe Langfuse enrichment for RAG and related AI traces: log retrieved identities and scores through the observability layer so operators can inspect retrieval quality without embedding the Langfuse SDK in `src/ai/*`.

## Requirements

### Requirement: Retrieved identities and scores appear on traces
When Langfuse is enabled and a RAG retrieval runs, observability MUST record retrieved chunk and/or note identities and retrieval scores on the relevant trace or span (not counts-only). Enrichment MUST go through `observability.tracing` (or equivalent observability helpers); application AI modules MUST NOT import the Langfuse SDK directly.

#### Scenario: Trace shows more than chunk count
- **GIVEN** Langfuse is configured and enabled
- **AND** a RAG chat or search path retrieves one or more chunks
- **WHEN** an operator inspects the resulting Langfuse trace
- **THEN** they can see retrieved identities (chunk and/or note ids) and associated scores
- **AND** the AI service code path did not import the Langfuse SDK directly

#### Scenario: Langfuse disabled is soft
- **GIVEN** Langfuse is not configured or disabled
- **WHEN** RAG retrieval runs
- **THEN** the request still succeeds
- **AND** missing tracing MUST NOT crash the API path

### Requirement: Scores can be attached for quality signals
The observability layer MUST support attaching numeric or categorical scores to traces (e.g. empty-retrieval or operator-defined quality markers) without requiring a second observability vendor. Scores used for hire-gate storytelling MUST remain honest about sample size and environment (local vs prod).

#### Scenario: Empty retrieval can be scored
- **GIVEN** a RAG request that returns zero retrieved chunks
- **WHEN** tracing completes with Langfuse enabled
- **THEN** the system MAY attach an empty-retrieval related score or structured marker on the trace
- **AND** documentation MUST NOT present local-only scores as production SLOs
