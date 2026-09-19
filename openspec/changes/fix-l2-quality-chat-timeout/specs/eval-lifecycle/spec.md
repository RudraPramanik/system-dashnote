## ADDED Requirements

### Requirement: Blueprint documents collection timeout as SKIP
The lifecycle blueprint and `evals/README.md` MUST list live quality-collection timeout and other request-transport failures as SKIP reasons, alongside non-200, empty answer, and empty retrieval. They MUST tell operators that an uncaught timeout traceback is a harness bug, that `--limit` is the smoke path for a slow stack, and that PowerShell MUST NOT paste `>>` comment lines from docs as commands. Operator docs MUST NOT include live JWT tokens.

#### Scenario: Operator finds timeout listed as SKIP
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/BLUEPRINT.md` or `evals/README.md`
- **THEN** they find that a timed-out `POST /ai/chat` collection is SKIP, not a crash
- **AND** they find that a full-set run with only timeout SKIPs is fail-closed (`n=0`), not a successful L2 close-out

#### Scenario: Operator command examples stay paste-safe on PowerShell
- **GIVEN** documented L2 commands
- **WHEN** an operator copies a command into PowerShell
- **THEN** examples do not require pasting `>>` comment lines
- **AND** examples do not embed a real JWT
