## 1. Scaffold the interview document

- [x] 1.1 Write `docs/documentation/qs2.md` header: title, purpose (interview passing + concept-clearance gate), format (Spoken / If they probe), statement that length is expected, and pointer to `qs.md`
- [x] 1.2 Add a table of contents matching design.md D2 sections 1–20 (plus How to use this doc)

## 2. Foundations and RAG core

- [x] 2.1 Write §1 LLM building blocks Q&A (tokens, context window, temperature, prompting vs weights, structured output) with Spoken + If they probe on every block
- [x] 2.2 Write §2 embeddings & chunking Q&A (what embeddings are, chunk size/overlap, metadata, embedding drift)
- [x] 2.3 Write §3 RAG architecture Q&A (index → retrieve → augment → generate; naive vs production RAG)

## 3. Enterprise RAG, retrieval, and indexing

- [x] 3.1 Write §4 RAG on an existing enterprise system / DB: source of truth, don’t dump the DB, SQL vs vectors, CDC/jobs, permission-aware retrieval, adding RAG without rewriting the monolith
- [x] 3.2 Write §5 retrieval quality Q&A covering chunking, embeddings, hybrid search, rerank, query rewrite, metadata filters, citations, and retrieval-vs-generation eval
- [x] 3.3 Write §6 vector stores & search backends Q&A (dedicated vector DB vs pgvector vs OpenSearch; filters before ANN)
- [x] 3.4 Write §7 indexing, sync, and freshness Q&A (incremental upserts, deletes, embed lag, idempotency)

## 4. Agents, latency, and cost

- [x] 4.1 Write §8 RAG chat vs agents Q&A stating both can coexist, with decision criteria (latency, tools, writes, HITL)
- [x] 4.2 Write §9 agent design Q&A (tools, loops, memory, HITL, blast radius, graph vs free-form ReAct, tool-calling safety)
- [x] 4.3 Write §10 latency Q&A covering TTFT vs E2E, streaming, caching layers, smaller/faster models, parallel retrieval, fewer agent hops, avoiding unnecessary tool loops
- [x] 4.4 Write §11 cost & capacity Q&A (token cost, batch embed, rate limits, model routing)

## 5. Production hire/no-hire topics

- [x] 5.1 Write §12 security, tenancy, prompt injection Q&A: retrieval filters from authenticated identity not the prompt; injection; tool permissions; PII; grounding
- [x] 5.2 Write §13 evaluation Q&A (goldens, retrieval vs generation, online eval; demo chat is not production-ready)
- [x] 5.3 Write §14 observability Q&A (traces, prompts, retrieval sets, cost/latency, user feedback)
- [x] 5.4 Write §15 failure modes & production ops Q&A (empty retrieval, provider outages, embed lag, fallbacks, circuit breakers)

## 6. Remaining sections and whiteboard

- [x] 6.1 Write §16 streaming & UX Q&A (SSE/tokens, partial answers, cancel, citation timing)
- [x] 6.2 Write §17 memory & conversations Q&A (thread history vs RAG context vs checkpoints; summarization)
- [x] 6.3 Write §18 fine-tuning vs RAG vs agents Q&A
- [x] 6.4 Write §19 system-design whiteboard Q&A (end-to-end production RAG, scale, SLOs)
- [x] 6.5 Write §20 counter-questions covering at least RAG vs fine-tuning, chat vs agent, and vector DB vs querying the existing SQL database

## 7. Cross-links, examples, and coverage check

- [x] 7.1 Add a short header pointer in `qs.md` to `qs2.md` without rewriting the DashNoteSystem Q&A
- [x] 7.2 Label any DashNoteSystem illustrations as **Example (DashNoteSystem):** and keep default answers vendor-neutral
- [x] 7.3 Walk the spec scenarios and design D2 must-include list; fill any missing required questions before considering apply complete
- [x] 7.4 If root README already lists `qs.md` as a job-prep doc, add `qs2.md`; otherwise leave README unchanged
