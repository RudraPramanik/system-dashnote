# L2 quality report

Rendered from `evals/quality_scores.jsonl`. The console transcript is not the record.

- environment: `lab`
- judge_model: `nvidia_nim/openai/gpt-oss-20b`
- n: 12
- SKIP: 0
- floor: 0.7 (correctness and completeness; style is not gated)

## Aggregates

- correctness: 0.8545
- completeness: 0.8333
- style: 1.0000

## Cases

### rag-ans-01-alpha-milestone

- correctness: 0.9000
  - reason: The response correctly states the milestone marker ALPHA_MARKER_7F3A, matching the key fact in the expected output. It omits the additional context about planning notes and delivery tracking, which is a harmless wording difference rather than a contradiction or invented fact, so the answer is largely aligned with the expected output.
- completeness: 0.5000
  - reason: The response correctly mentions ALPHA_MARKER_7F3A but fails to link it to the alpha project or milestone delivery, missing one of the two required checklist items.
- style: 1.0000
  - reason: The answer is concise, uses the exact marker token **ALPHA_MARKER_7F3A**, does not add extraneous information or citations, and matches the expected output. It follows the rubric and provides a correct, honest result.

### rag-ans-02-beta-checklist

- correctness: NaN
  - reason: judge error: empty judge response
- completeness: 0.9000
  - reason: The output correctly mentions BETA_MARKER_9C21 and states that it must pass before a release, matching the required points. The phrasing uses "beta public release" instead of the exact "public release", which is a minor deviation but does not omit any required content.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and preserves the marker token **BETA_MARKER_9C21** exactly as required by the rubric.

### rag-ans-03-gamma-infra

- correctness: 0.0000
  - reason: The actual output only contains the marker GAMMA_MARKER_44DE, whereas the expected output also includes the explanatory text “Gamma infra notes about Redis and queues are tagged GAMMA_MARKER_44DE.” The missing explanatory content is a factual mismatch, not a harmless wording difference, so the response does not align with the expected output.
- completeness: 0.5000
  - reason: The output correctly includes the marker GAMMA_MARKER_44DE, satisfying the first checklist item, but it fails to mention the connection to Redis or queue notes, which is the second required point. This partial compliance results in a moderate score.
- style: 1.0000
  - reason: The response is concise, uses the marker token exactly as required, and does not add any extraneous information or invented facts, fully meeting the rubric criteria.

### rag-ans-04-delta-rbac

- correctness: 1.0000
  - reason: Both outputs convey the same fact that the RBAC finding DELTA_MARKER_A1B2 is recorded in the Delta security review; the wording differences (e.g., capitalization, phrasing) are harmless and do not introduce contradictions.
- completeness: 1.0000
  - reason: The actual output includes the required marker DELTA_MARKER_A1B2 and explicitly frames it as an RBAC review finding, satisfying both checklist items.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and preserves the marker token exactly as required by the rubric.

### rag-ans-05-epsilon-evals

- correctness: 1.0000
  - reason: Both the actual and expected outputs contain the same factual information: the marker is EPSILON_MARKER_C0FF. There are no contradictions or invented facts, and the wording differences are harmless and therefore not penalized.
- completeness: 1.0000
  - reason: The actual output includes the required marker EPSILON_MARKER_C0FF and explicitly associates it with the eval harness, satisfying both checklist items.
- style: 1.0000
  - reason: The response is concise, does not add any extra information, and preserves the marker token exactly as required. It follows the rubric by providing only the necessary answer and no citation prose.

### rag-ans-06-zeta-workers

- correctness: 1.0000
  - reason: The actual output correctly states the marker value ZETA_MARKER_88EE, matching the key fact in the expected output. It does not contradict or add invented information, and the wording difference is harmless.
- completeness: 0.5000
  - reason: The response correctly mentions the marker ZETA_MARKER_88EE, satisfying one part of the expected checklist, but it fails to link the marker to ARQ/worker automation as required. This partial compliance results in a moderate score.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and preserves the marker token **ZETA_MARKER_88EE** exactly as required.

### rag-ans-07-eta-citations

- correctness: 1.0000
  - reason: The actual output conveys the same factual requirement as the expected output—citations must come from the metadata identified by ETA_MARKER_1122. The difference is only in wording (“metadata **ETA_MARKER_1122**” vs “metadata referenced by ETA_MARKER_1122”), which is a harmless variation and does not introduce any contradictions or invented facts.
- completeness: 1.0000
  - reason: The actual output includes both required checklist items: it mentions ETA_MARKER_1122 and states that citations must come from metadata, satisfying the expected requirement of citations coming from metadata or retrieved notes. No required point is missing.
- style: 1.0000
  - reason: The response is concise, does not invent facts, and preserves the required marker token exactly.

### rag-ans-08-alpha-planning

- correctness: 1.0000
  - reason: The actual output contains the same factual information as the expected output—both refer to the Alpha project planning and the milestone delivery under marker ALPHA_MARKER_7F3A. There are no contradictions or invented facts, and the differences are only in wording and formatting, which are harmless.
- completeness: 1.0000
  - reason: The actual output includes both required elements: it mentions the Alpha project and also references ALPHA_MARKER_7F3A milestone delivery, satisfying all checklist points.
- style: 1.0000
  - reason: The answer is concise, uses the marker token exactly, and does not add extraneous information or citations.

### rag-ans-09-beta-release-gate

- correctness: 1.0000
  - reason: The actual output conveys the same factual information as the expected output: BETA_MARKER_9C21 is a checklist item that must be completed before public release. The differences are only in wording and formatting (e.g., “pre‑release” vs. “checklist item that must be completed before public release” and bolding), which are harmless and do not introduce contradictions or invented facts.
- completeness: 1.0000
  - reason: The actual output contains both required elements: it mentions BETA_MARKER_9C21 and states that it must be completed before the public release, satisfying the completeness checklist.
- style: 1.0000
  - reason: The answer is concise, does not invent facts, and preserves the marker token exactly as required by the rubric.

### rag-ans-10-gamma-services

- correctness: 0.5000
  - reason: The actual output correctly lists Redis and Queue, matching the component names in the expected output, but it omits the required tag GAMMA_MARKER_44DE and the context that these are mentioned in the gamma infra notes. This partial alignment earns a moderate score.
- completeness: 0.6000
  - reason: The output correctly lists Redis and a queue, satisfying two of the three required checklist items. However, it omits the required mention of GAMMA_MARKER_44DE, so it fails to fully meet the expected output.
- style: 1.0000
  - reason: The answer is concise, uses the required marker tokens exactly, does not invent facts, and contains no unnecessary citation prose, fully meeting the rubric.

### rag-ans-11-delta-finding-id

- correctness: 1.0000
  - reason: The actual output contains the same identifier as the expected output and does not introduce any contradictions or invented facts; the omission of the introductory phrase is a harmless wording difference, so no penalty is applied.
- completeness: 1.0000
  - reason: The actual output contains the required marker exactly as specified in the expected output, meeting all checklist points.
- style: 1.0000
  - reason: The answer is concise, uses the exact marker token from the notes, does not invent facts, and follows the rubric’s requirement for a minimal response. It meets all specified criteria.

### rag-ans-12-epsilon-purpose

- correctness: 1.0000
  - reason: Both outputs correctly state that EPSILON_MARKER_C0FF is used as a golden case seed for retrieval/eval purposes, with no contradictions or invented facts. The wording differs but the factual content matches, so no penalty is warranted.
- completeness: 1.0000
  - reason: The actual output includes the required marker EPSILON_MARKER_C0FF and clearly states its purpose as a golden case seed for retrieval, satisfying all checklist items.
- style: 1.0000
  - reason: The response is concise, does not add extraneous information, and preserves the marker token **EPSILON_MARKER_C0FF** exactly as required. It follows the rubric by providing a clear answer without inventing facts or adding citation prose.
