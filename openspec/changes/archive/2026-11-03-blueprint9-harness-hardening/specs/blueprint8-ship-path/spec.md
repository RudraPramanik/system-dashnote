## ADDED Requirements

### Requirement: Blueprint 8 points to Blueprint 9 for harness hardening
`docs/documentation/blueprint8.md` MUST include a short pointer to `docs/documentation/blueprint9.md` as the harness-hardening successor to use after the product is alive. The pointer MUST NOT change Blueprint 8’s Tier 0 job-gate order, Alive law, or the rule that `/ai/chat*` and `/ai/agent*` both remain. The pointer MUST state that Blueprint 9 phase IDs (`9H.*`) are not the multi-agent Slice 9 product.

#### Scenario: Operator finds harness work without leaving the ship path
- **GIVEN** Blueprint 9 exists
- **WHEN** an operator reads Blueprint 8 for what to do after the Alive ship path
- **THEN** they find a pointer to `docs/documentation/blueprint9.md`
- **AND** Tier 0 and chat-versus-agent coexistence are unchanged
- **AND** the pointer distinguishes 9H harness hardening from multi-agent Slice 9
