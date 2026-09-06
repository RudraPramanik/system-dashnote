# Blueprint 8 — Alive Ship Path (operator default)

> **Follow this document first.** It is the locked ship path for hiring readiness and AI-engineering depth.  
> **Detail / Composer prompts** still live under [`blueprint/`](blueprint/) — do not orphan them.  
> **Day-by-day checklist:** [`docs/ship-plan.md`](../ship-plan.md) (locked to this file).  
> **Job-search boxes:** [`blueprint/goal.md`](blueprint/goal.md) · **7P tracker:** [`production.md`](production.md)

| Need | Open |
|------|------|
| Ship-path index (8X phases) | [`blueprint/slice8_X.md`](blueprint/slice8_X.md) |
| Thin CI | [`blueprint/slice8_ci.md`](blueprint/slice8_ci.md) |
| Platform / 7P prompts | [`blueprint/slice-platform.md`](blueprint/slice-platform.md) |
| Frontend B-gate | [`frontendguide.md`](frontendguide.md) |
| Eval harness (8X.2) | [`blueprint/slice8_eval.md`](blueprint/slice8_eval.md) |
| HITL API-first (8X.3) | [`blueprint/slice8_hitl.md`](blueprint/slice8_hitl.md) |
| Full slice map | [`blueprint/total.md`](blueprint/total.md) |

**Not this file:** optional GraphRAG productization (Slice 8 in `total.md`) and multi-agent supervisor (Slice 9) are **out of the default path** — see §GraphRAG intro and §Non-goals.

---

## Alive law

The product must stay **alive**: API + AI surfaces + frontend demo path remain deployable and demoable while you deepen quality.

| Alive means | Does **not** mean |
|-------------|-------------------|
| `dashnotesystemv1` API + worker can ship to VPS anytime | Every experiment runs on a 1–2GB VPS |
| Sibling `dashnotes` FE can demo chat, citations, agents, notes, files | Live demo depends on local rerankers or heavy judges |
| `/ai/chat*` and `/ai/agent*` **both** remain (chat ≠ agent) | Replacing chat with agent “to simplify” |
| CD / smoke / CI stay green | Melting VPS RAM for eval frameworks |

**VPS vs local split**

| Runs on small VPS / prod path | Local, fixture, or nightly only |
|------------------------------|----------------------------------|
| API, worker, nginx, hosted data plane | LLM-as-judge faithfulness suites |
| Langfuse tracing (SaaS) | Optional RAGAS batch jobs |
| Golden `run_eval.py` against live `--base-url` (operator) | Local reranker / heavy hybrid experiments |
| Fixture evals in PR CI | Anything that requires GPU or large local models |

Tier-2 or lab work that is hostile to a small VPS **must not** be required to claim the job gate, and **must not** make the stranger demo depend on it.

---

## Spine vs thicken

```
ALWAYS ON — Tier 0 job gate (hire minimum)
  Live API proof ──▶ FE stranger demo ──▶ Evals C-gate ──▶ Portfolio packaging
         │                                    │
         │                                    ▼
         │                         slice8_eval.md (8X.2)
         │                                    │
         ▼                                    ▼
  Keep Alive (demoable)              + Tier 1 thicken (HITL, Langfuse depth, …)
                                              │
                                              ▼
                                     Tier 2 lab (local/nightly OK)
```

Compatible with Slice 8X **deploy-first** calendar: CI → finish prod → frontend → evals → HITL  
(see [`slice8_X.md`](blueprint/slice8_X.md)). Blueprint8 adds Alive + Tier map on top; it does not invent a second contradictory order.

### Active window (2026-09) — local AI-depth-first Tier 1

VPS A-gate (HTTPS smoke / A4–A7) is deferred. Operators **MAY** implement Tier 1 deepeners (HITL, Langfuse depth, trajectory goldens, fixture CI) against the **local Compose + FE** Alive stack now.

This follows Slice 8X’s **alternate AI-depth-first** path — it is **not** a waiver of Tier 0 production proof.

| Allowed now | Still forbidden |
|-------------|-----------------|
| Local HITL / evals / Langfuse depth | Claiming **production-live** |
| Fixture CI gates | Claiming **hire-ready / job search** solely from local Tier 1 |
| Local cost/latency samples (label as local) | GraphRAG / multi-agent on the default path |

When VPS work resumes: close A4/A7 smoke before any production-live claim.

---

## Tier 0 — Job gate (mandatory before claiming hire-ready)

Aligned with [`goal.md`](blueprint/goal.md) A/B/C/D. **GraphRAG is not required.**

| Gate | What “done” looks like | Detail |
|------|------------------------|--------|
| **A — Production** | Hosted data plane + VPS smoke; TLS health; CI/CD present; do not claim production-live without smoke proof | [`production.md`](production.md) · 8X.4 |
| **B — Frontend** | Stranger can register → note/file → RAG with citation → agent mutation demo | [`frontendguide.md`](frontendguide.md) · goal §B |
| **C — Evaluation** | ≥10 golden cases (retrieval + tenant isolation), `run_eval.py` PASS X/Y, honest pass rate documented | [`slice8_eval.md`](blueprint/slice8_eval.md) · goal §C |
| **D — Packaging** | README pitch, live links, eval % + cost/latency, demo video, talk track | goal §D · ship-plan |

**Start applying only when Tier 0 boxes you need for your track are ✅.**

---

## Tier 1 — Ahead-of-most (production-valid deepeners)

Do these to stand out **without** breaking Alive. Prefer shipping on the real product path.

| # | Deepener | Notes | Detail |
|---|----------|-------|--------|
| 1 | **HITL** before agent `create_note` / `update_note` | API-first interrupt + resume; FE polish later | [`slice8_hitl.md`](blueprint/slice8_hitl.md) |
| 2 | **Langfuse depth** | Log retrieved chunk/note ids + scores (not counts only); scores on traces | `observe.md` / tracing |
| 3 | **Langfuse-native experiments** | Preferred thickener after C-gate: datasets + judges — **do not replace** golden JSONL harness | — |
| 4 | **Cost / latency table** | From Langfuse export or fixed sample; README field | goal §D4 |
| 5 | **Fixture evals in CI** | Deterministic only; never require live LLM keys for green PR | slice8_eval §8X.2.4 |
| 6 | **Agent trajectory goldens** | ≥5 cases incl. forbid surprise create (`required_tools` / `forbidden_tools` / `sequence_mode`) | slice8_eval §8X.2.3 |
| 7 | **Failure-mode notes** | Empty retrieval, LLM 503, embed lag — runbook / talk track | runbook |

**Eval stack preference (locked):** Langfuse-native (datasets / experiments / judges) primary after C-gate. Custom `evals/` remains the C-gate harness. RAGAS = optional nightly later. **DeepEval is not required** on this path.

---

## Tier 2 — Lab thickeners (local / nightly; not PR-blocking)

Top ~3–5% depth. Keep off the critical path to Tier 0.

| Item | Where it runs | Rule |
|------|---------------|------|
| recall@k / MRR on goldens | Local or nightly | Document in `evals/EXPERIMENTS.md` when implemented |
| Faithfulness / answer relevancy | Langfuse judges or optional RAGAS nightly | **Never** PR-blocking |
| EXPERIMENTS.md (before → change → after) | Repo docs | Shows measure→improve |
| Hybrid search / rerank lab | Local or slim API; promote only if VPS-safe | Only after baseline evals exist to beat |
| Synthetic query expansion | Local | Optional corpus growth |

---

## Eval → Improve → Gate loop

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  MEASURE     │────▶│  IMPROVE     │────▶│  GATE        │
│  goldens     │     │  threshold / │     │  CI fixture  │
│  Langfuse    │     │  prompt /    │     │  nightly live│
│  empty rate  │     │  chunking /  │     │  no merge if │
│  (judges*)   │     │  tools       │     │  regression  │
└──────────────┘     └──────────────┘     └──────────────┘
        ▲                                        │
        └──────── failing cases → new goldens ───┘

* judges = Tier 2 / nightly — not PR CI
```

C-gate = binary pass/fail on known cases + tenant isolation. Tier 2 adds ranked metrics and faithfulness so you can prove improvement, not just demos.

---

## GraphRAG — short introduction (not on the default path)

**Idea:** Beyond chunk vectors, extract entities and relationships (people, projects, decisions) into a graph so questions like “who decided X and what notes mention it?” can traverse links, not only cosine similarity.

**Why people reach for it:** multi-hop questions, workspace knowledge maps, “related notes” that sparse/dense retrieval miss.

**Why deferred here:** Neo4j (or equivalent) adds ops weight on a thin VPS; most hire demos and client RAG work do not need it; you already differentiate with RBAC retrieval, agents, evals, and HITL.

**Rule:** This section is an **introduction only**. GraphRAG / Neo4j productization is **not** required for Tier 0 or Tier 1. It remains optional (see Slice 8 in [`total.md`](blueprint/total.md)) until a later authorized change after production health is proven.

---

## Non-goals (default path)

- Neo4j / GraphRAG on the 1–2GB VPS as a hire-gate item  
- Multi-agent supervisor productization (Slice 9)  
- Live LLM-as-judge or paid live LLM keys required to green PR CI  
- DeepEval (or any second eval platform) as a required default  
- Replacing `/ai/chat*` with `/ai/agent*`  
- Blocking job search on hybrid/rerank, metering APIs, or scale caches  

---

## How to work day-to-day

1. Read **this file** for priorities (Alive + Tier 0 → 1 → 2).  
2. Execute Composer substages from the **detail** blueprints linked above.  
3. Track boxes in [`goal.md`](blueprint/goal.md) and days in [`ship-plan.md`](../ship-plan.md).  
4. Keep the demo alive after every change.
