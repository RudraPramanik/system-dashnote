## Why

Canonical `docs/documentation/system.md` is the routing hub, but it still lags `src/main.py`: `POST /ai/feedback` is mounted and L3 serving observability (`dashnote_ai_*`, Langfuse traces, thumbs) is live, while the system map, LLD, OpenSpec agent context, AI laws, and frontend guide still describe the pre-L3 HTTP surface. Agents and humans following the hub miss a live route and copy stale lists into sibling docs.

## What Changes

- Refresh `docs/documentation/system.md` so the router table, metrics, observability, and testing sections match the mounted API (including `ai_routes/feedback.py` / `POST /ai/feedback`) and current Prometheus series (`dashnote_api_*` plus low-cardinality `dashnote_ai_*`).
- Point the system map at the eval lifecycle (`evals/BLUEPRINT.md` / `evals/README.md`) as L0–L3 **implemented**, with L3 traces/thumbs **not** a production SLO and **not** the hard `/health` gate. Fix `evals/BLUEPRINT.md` status lines that still call L3 “this phase.”
- Align sibling keep-set docs that copy the HTTP surface from `system.md`: `ai.md` (router law), `lld.md` (composition / metrics), `frontendguide.md` (optional client feedback), `openspec/config.yaml` (HTTP surface + product domains), and README documentation/architecture bullets if they omit feedback.
- Keep existing dual observe pointers (`observe.md` + `observability.md`) and production-honesty (HTTP-IP first-boot ≠ HTTPS / A7). Do **not** claim production-grade startup or mid-enterprise.
- **Non-goals:** application code, new APIs, deleting/merging the `consolidate-docs` retire-set, rewriting `qs*.md` / historical blueprint slices, implementing TLS, or treating traces as SLOs.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `canonical-docs`: System and related canonical architecture docs MUST list `POST /ai/feedback` on the mounted HTTP surface, document `dashnote_ai_*` quality counters alongside `dashnote_api_*`, and MUST NOT describe L3 traces or thumbs as the deploy gate or a production SLO. The system map MUST stay the hub that sibling keep-set docs do not contradict.
- `frontend-developer-guide`: Frontend guide MUST document `POST /ai/feedback` as an optional JWT-scoped client call (`thread_id` + thumbs or 1–5; no `workspace_id` override). It MUST NOT require feedback UI for B-gate.

## Impact

- **Docs / OpenSpec context only** — no FastAPI, worker, schema, Nginx, or Compose behavior changes.
- Touched files (planned): `docs/documentation/system.md`, `ai.md`, `lld.md`, `frontendguide.md`; `evals/BLUEPRINT.md` (status lines only); `openspec/config.yaml`; `readme.md` if the live-surface list is stale.
- In-flight `consolidate-docs` still owns deletions. This change MUST NOT delete files or collapse the dual observability guides.
- Tenancy / chat≠agent / hard-vs-soft health: unchanged. Feedback stays JWT `wid` only.
