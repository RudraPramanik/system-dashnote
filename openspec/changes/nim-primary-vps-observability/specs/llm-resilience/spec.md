## ADDED Requirements

### Requirement: Default candidates prefer Lightning NIM then Gemini
Documented code defaults and example env files MUST set `LLM_MODEL` to `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b`. `LLM_MODEL_FALLBACKS` MUST list `gemini/gemini-2.5-flash` when a Gemini key is expected, and MUST NOT list `nvidia_nim/openai/gpt-oss-20b`, Nemotron Super 120B, or Ultra 550B. Operators MAY still pin Super 120B, Ultra, or `gpt-oss-20b` explicitly. Completions MUST NOT enable unbounded hidden reasoning traces that ignore `LLM_MAX_TOKENS`. Chat and agent routes MUST both remain. Gone, timeout, and rate-limit walks MUST keep their existing order and error frames. Documentation MUST note that NIM free tiers are typically higher RPM than Gemini free tiers, so product defaults prefer the small NIM id for routine chat.

#### Scenario: Example env prefers Lightning then Gemini
- **GIVEN** an operator copies `.env.example` or `.env.production.example` without overriding model ids
- **WHEN** they inspect `LLM_MODEL` and `LLM_MODEL_FALLBACKS`
- **THEN** the primary is `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b`
- **AND** the fallback includes `gemini/gemini-2.5-flash`
- **AND** `gpt-oss-20b` does not appear
- **AND** Super 120B does not appear

#### Scenario: Operator may still pin Super for quality
- **GIVEN** an operator sets `LLM_MODEL` to `nvidia_nim/nvidia/nemotron-3-super-120b-a12b`
- **AND** `LLM_MODEL_FALLBACKS` includes Gemini Flash
- **WHEN** that Super id is live
- **THEN** the system MUST honor the explicit Super primary
- **AND** the wall-clock abort, model-gone, and rate-limit fallback rules still apply

#### Scenario: NIM rate-limit walks to Gemini
- **GIVEN** Lightning returns HTTP 429 or a rate-limit error
- **AND** Gemini Flash is live
- **WHEN** a completion walks candidates
- **THEN** the request completes using Gemini Flash
- **AND** the rate-limited NIM id is not sticky as the cached primary

## REMOVED Requirements

### Requirement: Default candidates prefer Gemini Flash then a small NIM
**Reason**: Gemini free-tier RPM is lower than the typical NVIDIA NIM free allowance (~40 RPM). Product chat should spend the NIM budget first and use Gemini as the hatch.
**Migration**: Defaults and example env files use Lightning NIM first and Gemini Flash second. Operators who want Gemini-first set `LLM_MODEL=gemini/gemini-2.5-flash` themselves. Recreate `api` and `worker` after changing the VPS env so the in-process cache clears.
