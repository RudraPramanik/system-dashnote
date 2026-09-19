## ADDED Requirements

### Requirement: Third implementation phase after L1 is L2 LLM-as-judge quality
The lifecycle blueprint MUST name L2 (LLM-as-judge answer quality against frozen RAG answer goldens) as the third implementation phase after L0 fixture-gate close-out and L1 live contract. That phase MUST close `evals/golden/rag_answers.jsonl`, `evals/run_quality.py`, a laptop-only quality requirements file, operator docs for JWT live collection + dedicated judge credential, the NVIDIA NIM Gemini-429 hatch for the product stack during collection, and an honest recorded quality run (`n`, SKIPs, per-metric aggregates, environment `lab` or `pre-deploy`). It MUST NOT require shipping agent answer goldens, threshold/baseline EXPERIMENTS automation, generator prompt rewrites, or a PR-blocking judge workflow. PR CI MUST remain L0 fixture-only. Later phases (thresholds, style-driven generator work, agent quality) remain separate changes.

#### Scenario: This change ships the RAG quality suite not agent or CI judge
- **GIVEN** the L2 implementation change is complete
- **WHEN** an operator inspects `evals/`
- **THEN** `evals/run_quality.py` and `evals/golden/rag_answers.jsonl` exist
- **AND** agent answer goldens are not required to exist yet
- **AND** PR CI still runs fixture mode only
- **AND** the blueprint still lists thresholds / agent answers as later phases

#### Scenario: Blueprint roadmap order is L0 then L1 then L2
- **GIVEN** the lifecycle blueprint phased roadmap
- **WHEN** an implementer plans the next eval change after L1
- **THEN** L2 LLM-as-judge is the named next phase
- **AND** L1 live contract remains listed as done before L2

### Requirement: Blueprint documents L1/L2 alignment
The lifecycle blueprint MUST state that L2 answer collection aligns with the L1 live contract: same JWT `wid` tenancy, same seed / marker ID law (reuse retrieval seeds where possible), same Compose/staging target class, and the same NVIDIA NIM hatch when Gemini 429 blocks product chat/embed. L2 MUST score answer quality with a separate judge suite and MUST NOT replace L0/L1 PASS/FAIL contract scoring. The blueprint MUST NOT present L2 as a second unrelated live stack.

#### Scenario: Operator sees L2 on top of L1
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator reads the L1 and L2 layer descriptions
- **THEN** they are told L2 collects `/ai/chat` answers on a live stack proven by L1-class auth and tenancy
- **AND** they are told L0/L1 remain the retrieval/tenant contract and C-gate
- **AND** they are told Gemini 429 on product collection uses NVIDIA NIM (different free model), not a judge on the hot path

### Requirement: Blueprint marks quality CLI as implemented for L2
The lifecycle blueprint and `evals/README.md` MUST document the quality CLI as the implemented L2 operator/pre-deploy command (not merely planned), including fail-closed behavior, dedicated judge key, and required terminal honesty fields. RAGAS and Langfuse labs MUST remain documented until a later change explicitly folds or retires them.

#### Scenario: Operator finds the runnable quality command
- **GIVEN** the L2 implementation change is complete
- **WHEN** an operator opens `evals/BLUEPRINT.md` or `evals/README.md`
- **THEN** they find how to run `evals/run_quality.py`
- **AND** they find that scores are labeled `lab` or `pre-deploy`, not production SLOs
- **AND** they can still find RAGAS and Langfuse operator paths
