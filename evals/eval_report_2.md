# L2 quality report

Rendered from `evals/quality_scores.jsonl`. The console transcript is not the record.

- environment: `lab`
- judge_model: `nvidia_nim/openai/gpt-oss-20b`
- n: 12
- SKIP: 0
- floor: 0.7 (correctness and completeness; style is not gated)

## Aggregates

- correctness: 0.9000
- completeness: 0.7417
- style: 1.0000

## Cases

### rag-ans-01-alpha-milestone

- correctness: 0.8000
  - reason: The response correctly identifies the milestone marker ALPHA_MARKER_7F3A, matching the key fact in the expected output. It does not introduce any contradictions or invented details. The only shortfall is the omission of the surrounding context (“planning notes” and “delivery tracking”), which is a harmless wording difference per the evaluation rules.
- completeness: 0.5000
  - reason: The output correctly mentions the marker ALPHA_MARKER_7F3A but does not provide the required link to the alpha project or milestone delivery, missing one of the two checklist items.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, preserves the marker token exactly, and contains no citation prose, fully meeting the rubric requirements.

### rag-ans-02-beta-checklist

- correctness: 1.0000
  - reason: Both outputs correctly state that BETA_MARKER_9C21 is part of the checklist before the public release, with no contradictions or invented facts. The wording differs slightly but the factual content aligns perfectly.
- completeness: 1.0000
  - reason: The actual output includes the marker BETA_MARKER_9C21 and states that it must pass before the beta public release, satisfying both checklist items: mention of the marker and the requirement before public release.
- style: 1.0000
  - reason: The answer is concise, uses the marker token exactly, does not add extra information, and follows the rubric.

### rag-ans-03-gamma-infra

- correctness: 0.0000
  - reason: The actual output only contains the marker GAMMA_MARKER_44DE, whereas the expected output also includes the explanatory phrase “Gamma infra notes about Redis and queues are tagged GAMMA_MARKER_44DE.” The missing explanatory text means the facts in the actual output do not match the expected facts, resulting in a score of 0.
- completeness: 0.5000
  - reason: The output includes the required marker GAMMA_MARKER_44DE but fails to mention its connection to Redis or queue notes, which is a second required point in the checklist. Consequently, the response is incomplete and receives a lower score.
- style: 1.0000
  - reason: The answer is concise, uses the marker token exactly as required, and contains no invented facts or additional prose, fully meeting the rubric’s criteria.

### rag-ans-04-delta-rbac

- correctness: 1.0000
  - reason: The actual output correctly states the RBAC finding DELTA_MARKER_A1B2, matching the key fact in the expected output. It does not introduce any contradictions or invented information, and the wording differences are harmless. Therefore the response aligns fully with the evaluation steps.
- completeness: 1.0000
  - reason: The actual output includes the required marker DELTA_MARKER_A1B2 and explicitly states it is an RBAC review finding, satisfying both checklist items.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and correctly preserves the marker token **DELTA_MARKER_A1B2** as required. It meets the rubric criteria and provides a valid response.

### rag-ans-05-epsilon-evals

- correctness: 1.0000
  - reason: The actual output correctly states the marker EPSILON_MARKER_C0FF, matching the expected output’s key fact. There are no contradictions or invented facts, and the wording differences are harmless. Therefore the response fully aligns with the evaluation steps.
- completeness: 1.0000
  - reason: The actual output includes the required marker EPSILON_MARKER_C0FF and explicitly states it is the golden seed marker used for the epsilon retrieval eval harness, thereby covering all checklist items: mention of the marker, association with eval, golden, and retrieval harness.
- style: 1.0000
  - reason: The response is concise, uses the exact marker token **EPSILON_MARKER_C0FF**, and does not add any extraneous information or citations, fully meeting the rubric requirements.

### rag-ans-06-zeta-workers

- correctness: 1.0000
  - reason: The response correctly states the marker value ZETA_MARKER_88EE, matching the key fact in the expected output. It omits the additional context about the zeta workers automation note, but this is a harmless wording difference and does not introduce contradictions or invented facts.
- completeness: 0.5000
  - reason: The output correctly mentions the marker ZETA_MARKER_88EE but fails to include the required link to ARQ/worker automation, missing one of the two checklist items.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and preserves the marker token **ZETA_MARKER_88EE** exactly as required by the rubric.

### rag-ans-07-eta-citations

- correctness: 1.0000
  - reason: The actual output states that citations must come from metadata **ETA_MARKER_1122**, which matches the expected requirement that citations come from metadata referenced by ETA_MARKER_1122. There are no contradictions or invented facts, and the difference is only in formatting, not meaning.
- completeness: 0.8000
  - reason: The output correctly mentions ETA_MARKER_1122 and states that citations must come from metadata, covering two of the three checklist items. However, it omits the requirement to reference retrieved notes, so one required point is missing.
- style: 1.0000
  - reason: The answer is concise, uses the required marker token exactly, does not invent facts, and contains no unnecessary citation prose, fully meeting the rubric.

### rag-ans-08-alpha-planning

- correctness: 1.0000
  - reason: The actual output contains the same factual content as the expected output—both mention the Alpha project, milestone delivery, and marker ALPHA_MARKER_7F3A—without any contradictions or invented facts, and wording differences are harmless.
- completeness: 1.0000
  - reason: The actual output includes both required elements: it references the Alpha project and the ALPHA_MARKER_7F3A milestone delivery, satisfying the checklist completely.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and preserves the marker token ALPHA_MARKER_7F3A exactly as required by the rubric.

### rag-ans-09-beta-release-gate

- correctness: 1.0000
  - reason: Both outputs convey the same factual information: BETA_MARKER_9C21 is a checklist item that must be completed before public release. The actual output adds the adjective "pre‑release" and uses a dash, but these are harmless wording differences and do not introduce contradictions or invented facts.
- completeness: 1.0000
  - reason: The actual output includes the required mention of BETA_MARKER_9C21 and clearly states it is a pre‑release item that must be completed before the public release, satisfying both checklist points.
- style: 1.0000
  - reason: The answer is concise, uses the marker token exactly, does not invent facts, and contains no unnecessary citation prose, fully meeting the rubric requirements.

### rag-ans-10-gamma-services

- correctness: 1.0000
  - reason: The actual output lists Redis and Queue, which matches the expected facts that the gamma infra notes mention Redis and queue components. There are no contradictions or invented facts, and the missing tag is a harmless wording difference.
- completeness: 0.6000
  - reason: The output lists Redis and Queue, satisfying two of the three checklist items, but it omits the required mention of GAMMA_MARKER_44DE when available, so it does not fully meet the expected output.
- style: 1.0000
  - reason: The answer is concise, contains no invented facts, and does not include any citation prose. It meets the rubric’s requirement to be brief and factual. No marker tokens are misused, and the response is appropriate for the given parameters.

### rag-ans-11-delta-finding-id

- correctness: 1.0000
  - reason: The actual output contains the same identifier DELTA_MARKER_A1B2 as the expected output, with no contradictions or invented facts. The difference in wording (“The recorded finding identifier is”) is harmless and does not affect factual correctness, so the response fully meets the evaluation criteria.
- completeness: 0.0000
  - reason: The actual output contains the marker surrounded by asterisks, whereas the expected output requires the marker to appear exactly as "DELTA_MARKER_A1B2" with no additional characters. This mismatch means the required checklist point is not satisfied.
- style: 1.0000
  - reason: The answer is concise, preserves the marker token exactly, does not invent facts, and contains no additional citation prose, fully meeting the rubric requirements.

### rag-ans-12-epsilon-purpose

- correctness: 1.0000
  - reason: The actual output contains the same factual content as the expected output—both mention the golden case seed EPSILON_MARKER_C0FF and its use for retrieval. There are no contradictions or invented facts, and the differences are only in wording, which is harmless.
- completeness: 1.0000
  - reason: The actual output includes the required marker EPSILON_MARKER_C0FF and clearly states its purpose as a golden case seed for retrieval, satisfying all checklist items.
- style: 1.0000
  - reason: The answer is concise, uses the marker token **EPSILON_MARKER_C0FF** exactly as required, and does not add any extraneous information or citations. It follows the rubric perfectly.
