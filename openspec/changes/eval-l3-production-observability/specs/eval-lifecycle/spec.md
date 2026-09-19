## ADDED Requirements

### Requirement: Fourth implementation phase after L2 is L3 production observability
The lifecycle blueprint MUST name L3 (production observability: Langfuse traces, Prometheus health, and user feedback) as the fourth implementation phase after L0 fixture-gate close-out, L1 live contract, and L2 LLM-as-judge quality. That phase MUST close operator docs for traces / `POST /ai/feedback` / `/metrics`, production-shaped Langfuse env wiring so existing keys enable the client, and an honest apply proof that a real turn emits a trace and feedback succeeds. It MUST NOT require shipping thresholds/baseline automation, generator prompt rewrites, agent answer goldens, or a PR-blocking judge workflow. PR CI MUST remain L0 fixture-only. Serving `/ai/chat` and `/ai/agent` MUST NOT await an LLM-as-judge. Later phases (thresholds, style-driven generator work, agent quality) remain separate changes.

#### Scenario: This change ships observability not a judge on the hot path
- **GIVEN** the L3 implementation change is complete
- **WHEN** an operator inspects serving and `evals/`
- **THEN** Langfuse traces, Prometheus quality counters, and `POST /ai/feedback` are the documented L3 surfaces
- **AND** `/ai/chat` and `/ai/agent` still return without waiting on GEval or RAGAS
- **AND** PR CI still runs fixture mode only
- **AND** the blueprint still lists thresholds / agent answers as later phases

#### Scenario: Blueprint roadmap order is L0 then L1 then L2 then L3
- **GIVEN** the lifecycle blueprint phased roadmap
- **WHEN** an implementer plans the next eval change after L2
- **THEN** L3 production observability is the named next phase
- **AND** L2 LLM-as-judge remains listed as done before L3
- **AND** L0/L1 remain listed as the shared contract beneath L2/L3

### Requirement: Blueprint documents L2/L3 alignment
The lifecycle blueprint MUST state that L3 serving observability aligns with prior layers: the same JWT `wid` tenancy as L1/L2 for traces and feedback; L0/L1 remain the retrieval/tenant `PASS: X/Y` contract; L2 remains the pre-deploy GEval suite; L3 MUST NOT replace those scores with traces or thumbs. Sampled Langfuse faithfulness MUST stay operator/nightly and MUST NOT run on the request path. The blueprint MUST NOT present L3 as a second unrelated eval corpus.

#### Scenario: Operator sees L3 beside L0/L1/L2 not instead of them
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator reads the L2 and L3 layer descriptions
- **THEN** they are told L3 traces and feedback use JWT `wid` only
- **AND** they are told L0/L1 remain the C-gate / live contract
- **AND** they are told L2 GEval stays off `/ai/chat` and `/ai/agent`
- **AND** they are told thumbs and traces are not production SLOs

### Requirement: Blueprint keeps L0/L1 alignment while closing L3
The lifecycle blueprint MUST keep the existing L0/L1 alignment contract: both modes share the same `evals/golden/` corpus and scorers; fixtures are the recorded form of the live contract; fixture-only and unwired live trajectories SKIP in L1. Closing L3 MUST NOT split L0 and L1 into separate corpora or change PR CI away from fixture-only.

#### Scenario: L0/L1 alignment survives the L3 close-out
- **GIVEN** the L3 implementation change is complete
- **WHEN** an operator reads `evals/BLUEPRINT.md` and `evals/README.md`
- **THEN** they still find that L0 and L1 share goldens and scoring for eligible cases
- **AND** they are told L0 is the PR CI recorded form and L1 is the live proof
- **AND** they are told L3 does not replace that contract

### Requirement: Blueprint marks L3 observability as implemented
The lifecycle blueprint and `evals/README.md` MUST document L3 as the implemented production-serving observability layer (not merely an unlabeled “exists” box), including Langfuse UI, `POST /ai/feedback`, Prometheus `/metrics`, soft tracing, and the rule that serving MUST NOT await a judge. RAGAS and Langfuse sampled-faithfulness labs MUST remain documented until a later change explicitly folds or retires them.

#### Scenario: Operator finds the runnable L3 surfaces
- **GIVEN** the L3 implementation change is complete
- **WHEN** an operator opens `evals/BLUEPRINT.md` or `evals/README.md`
- **THEN** they find how to confirm traces, submit feedback, and scrape quality counters
- **AND** they find that L3 is serving observability, not a merge gate and not a production SLO
- **AND** they can still find L0 fixture, L1 live, and L2 quality commands
