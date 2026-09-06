## 1. A-gate — production-live evidence

- [x] 1.1 Confirm hosted data plane + VPS `.env` / deploy path still match `docs/deployment/runbook.md` (no secrets committed)
- [ ] 1.2 Run `GET https://<prod-api>/health` and record hard-dependency success (A7) — **blocked: need prod URL from operator**
- [ ] 1.3 Run `scripts/smoke_prod.py` with `SMOKE_BASE_URL=https://<prod-api>` and require exit 0 (A4); fix deploy/app only if hard checks fail — **blocked: need prod URL** (local `http://127.0.0.1` smoke PASS 2026-09-06)
- [x] 1.4 Update `docs/documentation/blueprint/goal.md` A-gate boxes that match proven live smoke/TLS; leave unverified items unchecked
- [x] 1.5 Spot-check runbook production-gate checklist language still forbids claiming production-live without smoke

## 2. B-gate — API CORS + stranger demo proof

- [x] 2.1 Ensure `CORS_ORIGINS` (settings / `.env` / `.env.production.example`) includes the sibling FE origin for local and prod as needed
- [x] 2.2 Verify or document FE base URL wiring against the target API using `docs/documentation/frontendguide.md` B1–B7
- [x] 2.3 Operator: prove stranger demo path (register → note → file → RAG citation from `metadata` → agent mutation) against target API via sibling `dashnotes` (UI edits outside this apply root if gaps remain) — Playwright `e2e/b-gate.spec.ts` **3 passed** vs local API
- [x] 2.4 Update `goal.md` B1–B7 only for proven items; keep chat≠agent both in the demo

## 3. C-gate — eval harness schema and fixtures

- [x] 3.1 Create `evals/` layout: `golden/`, `run_eval.py`, `README.md` per `slice8_eval.md` / `ai-eval-harness` (modes, seed/fixture ID laws, PYTHONPATH)
- [x] 3.2 Define golden case schema (retrieval + tenant isolation fields) and document seed vs fixture ID strategy in `evals/README.md`
- [x] 3.3 Add ≥10 golden cases spanning retrieval relevance and tenant isolation (`retrieval.jsonl`, `tenant_isolation.jsonl` or equivalent)
- [x] 3.4 Implement dual-token or fixture path so member-vs-owner private-note isolation is automated (never forge workspace from body)

## 4. C-gate — runner CLI and proof

- [x] 4.1 Implement `evals/run_eval.py` with fixture|live modes, `--base-url` / token args, and `PASS: X/Y` summary with failing case ids
- [x] 4.2 Document how to run with `src` importable; smoke a fixture-mode run without live LLM keys
- [x] 4.3 Run live mode against local or prod API; record honest pass rate (target ≥80%) in `evals/README.md` and/or root README
- [x] 4.4 Update `goal.md` C1–C4 from recorded runner output; do not invent 100% if failures remain
- [x] 4.5 Confirm PR CI still does not require live LLM keys (fixture CI wire as blocking job is Tier 1 — document only if touched)

## 5. D-gate — portfolio packaging

- [x] 5.1 Update root README pitch, stack, architecture links; add live API/app URLs only after A/B evidence (else explicit pending)
- [x] 5.2 Add or fill eval pass-rate and cost/latency fields (Langfuse export or fixed sample; pending allowed if method stated) — eval rate filled; cost/latency explicit pending + method
- [x] 5.3 Add demo video link field (Loom/YouTube) and screenshots/GIF placeholders or assets when available — fields present as pending in README
- [x] 5.4 Add `docs/interview-talk-track.md` (2-min pitch + ≥3 tradeoffs)
- [ ] 5.5 Set GitHub topics (`rag`, `langgraph`, `fastapi`, `qdrant` or equivalent) when repo hosting allows — `gh` not installed; topics listed in README for manual set
- [x] 5.6 Update `goal.md` D1–D6 to match what actually shipped

## 6. Alive / regression checks

- [x] 6.1 Confirm local `docker compose` hard health still works after any settings/docs/evals changes
- [x] 6.2 Confirm `/ai/chat*` and `/ai/agent*` both remain; no HITL/GraphRAG/multi-agent scope creep in this change
- [ ] 6.3 Final pass: blueprint8 Tier 0 boxes needed for the employment track are ✅ in `goal.md` before starting a Tier 1 change — **blocked on A1/A4/A7 + B4/B7 + D2–D5**
