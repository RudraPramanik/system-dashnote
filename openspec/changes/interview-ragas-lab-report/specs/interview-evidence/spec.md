## Purpose

Hire and portfolio evidence for the operator RAGAS lab: a shareable, secrets-safe report that presents honest lab metrics alongside the fixture C-gate, without claiming production SLOs.

## ADDED Requirements

### Requirement: Shareable RAGAS lab report exists
The repository MUST include a Markdown RAGAS lab report under `docs/` or `evals/` that an operator can share for interviews or hiring review. The report MUST describe: (1) the fixture C-gate vs operator lab split, (2) how the lab collects question / answer / retrieved context and scores faithfulness plus context precision (or equivalent), (3) a dated results table including sample size `n`, SKIP or failure counts, judge model identity, and environment label `lab` or `live-local`, and (4) explicit caveats that scores are not production SLOs and are not PR CI gates.

#### Scenario: Interviewer can read architecture and results in one doc
- **GIVEN** this change is complete
- **WHEN** a reader opens the RAGAS lab report
- **THEN** they find both the eval architecture framing and a dated results table
- **AND** the report states that RAGAS is operator/nightly lab only (not VPS, not PR CI, not a production SLO)

#### Scenario: Report remains useful when a live run was blocked
- **GIVEN** a live lab attempt collected zero rows due to API or chat errors
- **WHEN** the report is updated for that attempt
- **THEN** the report MUST record the blocked outcome and failure mode honestly
- **AND** MUST NOT invent faithfulness or context-precision scores for uncollected rows

### Requirement: Report secrets hygiene
The RAGAS lab report and any linked interview screenshots or pasted command examples in that report MUST NOT contain access JWTs, refresh tokens, `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, Langfuse secrets, or other live credentials. Command examples MUST use placeholders such as `<access_token>`.

#### Scenario: Shared report has no live credentials
- **GIVEN** this change is complete
- **WHEN** an operator reviews the report Markdown for sharing
- **THEN** no live JWT or API key material appears in the file
- **AND** run instructions use credential placeholders

### Requirement: Report is discoverable from eval and interview docs
`evals/README.md` MUST link to the RAGAS lab report. If `docs/interview-talk-track.md` exists, it MUST point to the report (and/or EXPERIMENTS EXP-004) when discussing faithfulness or LLM-as-judge evidence.

#### Scenario: Operator finds the report from evals README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find a link or clear pointer to the RAGAS lab report

#### Scenario: Talk track points at lab evidence when present
- **GIVEN** `docs/interview-talk-track.md` exists after this change
- **WHEN** a candidate reviews faithfulness / judge talking points
- **THEN** they find a pointer to the RAGAS lab report or the EXPERIMENTS RAGAS loop
