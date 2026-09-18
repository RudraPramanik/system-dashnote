## ADDED Requirements

### Requirement: L1 live contract uses the same goldens and scoring as L0
The live eval runner (`evals/run_eval.py --mode live`) MUST execute eligible retrieval and tenant-isolation goldens from the same `evals/golden/` corpus used by fixture mode. Scoring MUST use the same marker / min-max hit / isolation rules as L0. Cases with `mode_hint` of `fixture` (or listed in `skip_if_modes` for `live`) MUST be SKIPPED, not failed. Agent trajectory cases MAY remain fixture-primary; when live trajectory is not wired, the runner MUST SKIP them with an explicit reason rather than FAIL. L0 fixtures MUST remain the recorded form of the same contract — not a separate golden set.

#### Scenario: Shared scoring for an either-mode retrieval case
- **GIVEN** a retrieval golden with `mode_hint` `either` and content markers
- **AND** the live API returns hits whose text contains those markers
- **WHEN** the operator runs `--mode live` with a valid JWT
- **THEN** the case is marked PASS using the same scoring rules as fixture mode

#### Scenario: Fixture-only cases skip in live
- **GIVEN** a golden with `mode_hint` `fixture` or `skip_if_modes` including `live`
- **WHEN** the operator runs `--mode live`
- **THEN** that case is reported as SKIP with a clear reason
- **AND** it does not count as FAIL in the aggregate denominator of scored cases (SKIP count is still reported)

#### Scenario: L0 remains the CI-recorded form of the contract
- **GIVEN** this change is complete
- **WHEN** an operator compares L0 and L1
- **THEN** docs state that fixture payloads are the recorded L1 contract for the same case ids
- **AND** PR CI continues to run fixture mode only

### Requirement: L1 live runner authenticates with JWT and scopes by wid
Live L1 MUST call the real API with Bearer JWT(s). Retrieval scope MUST come from the token’s workspace (`wid`) only. Forged workspace query/body fields MUST NOT expand results. Dual-token tenant cases that need a member actor MUST require `--token-b` (or documented env equivalent); without it those cases MUST SKIP with an explicit reason, not silently use the owner token as the member.

#### Scenario: Live search uses JWT workspace only
- **GIVEN** a reachable API and a valid access token
- **WHEN** live mode runs a retrieval or forged-workspace case
- **THEN** workspace scoping comes from the JWT only
- **AND** a forged workspace identifier MUST NOT return cross-tenant hits

#### Scenario: Member deny needs token-b
- **GIVEN** a tenant-isolation case with `actor` `b`
- **AND** `--token-b` is unset
- **WHEN** live mode reaches that case
- **THEN** the case is SKIPPED with a message that names the missing second token
- **AND** it is not scored as PASS using `--token` alone

### Requirement: L1 apply records an honest live pass rate
Operators MUST be able to run live mode against a reachable base URL after this change and record the actual `PASS: X/Y` in `evals/README.md`, including SKIP count and reasons, with environment labeled `live-local` (or staging). The documented rate MUST match that run. A previous dated live row MUST NOT be reused as proof that this change works. Zero scored cases with only SKIPs MUST NOT be documented as a successful L1 close-out.

#### Scenario: Fresh live summary is recorded
- **GIVEN** this change’s apply has run `evals/run_eval.py --mode live` against a real stack with at least one scored case
- **WHEN** an operator opens `evals/README.md`
- **THEN** the latest recorded live row matches that run’s `PASS: X/Y`
- **AND** SKIP count/reasons are visible in the row or adjacent notes
- **AND** the text does not claim success from an older live run

### Requirement: Operator docs name L1 live procedure and NIM hatch for Gemini 429
`evals/README.md` and `evals/BLUEPRINT.md` MUST document how to run L1 (`--mode live`, `--base-url`, `--token`, optional `--token-b`, `--seed-live`), that L1 is operator/nightly and not a PR merge gate, and that if Gemini rate-limit / 429 blocks the live stack (embed, chat fallback, or related product LLM path), operators MUST use NVIDIA NIM with a different free/catalog model via `LLM_MODEL` / `LLM_MODEL_FALLBACKS` and recreate `api` + `worker`. That hatch MUST NOT put an LLM-as-judge on `/ai/chat` or `/ai/agent`, and MUST NOT be required to green L0 fixture CI.

#### Scenario: Operator can run L1 from the README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find the live command with base URL and token
- **AND** they find that PR CI stays fixture-only
- **AND** they find the NVIDIA NIM (different free model) hatch for Gemini 429 on the live stack

#### Scenario: Blueprint places L1 between L0 and L2
- **GIVEN** this change is complete
- **WHEN** an operator opens the phased roadmap in `evals/BLUEPRINT.md`
- **THEN** L1 live contract is listed as the phase after L0
- **AND** DeepEval / `run_quality.py` remains a later phase
