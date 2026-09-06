# Eval harness (Tier 0 / C-gate)

Golden corpus + CLI for retrieval quality and tenant isolation. Aligns with
`docs/documentation/blueprint/slice8_eval.md` and `openspec/specs/ai-eval-harness`.

## Layout

```
evals/
  README.md
  golden/
    retrieval.jsonl
    tenant_isolation.jsonl
  fixtures/          # recorded responses for --mode fixture
  run_eval.py
```

## Runner modes

| Mode | Flag | Behavior |
|------|------|----------|
| **fixture** | `--mode fixture` | Loads recorded JSON under `evals/fixtures/`. No live LLM keys. |
| **live** | `--mode live` | Calls HTTP API (`--base-url` + `--token`). Prefer local Compose or prod. |

PR CI must not require `--mode live` or paid LLM keys. Wiring fixture evals as a
blocking CI job is a **Tier 1** thickener; this harness only documents readiness.

## PYTHONPATH / how to run

`evals/` lives outside `src/`. From repo root:

```powershell
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode fixture

# Live against local nginx edge (docker compose up):
$env:PYTHONPATH = "src"
python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token "<access_token>"
```

```bash
PYTHONPATH=src python evals/run_eval.py --mode fixture
PYTHONPATH=src python evals/run_eval.py --mode live --base-url http://127.0.0.1 --token "$TOKEN"
```

Exit code `0` only when all selected cases pass. Summary line: `PASS: X/Y`.

### Dual tokens (tenant live)

```powershell
python evals/run_eval.py --mode live --base-url http://127.0.0.1 `
  --token "<owner_or_user_a_jwt>" --token-b "<member_user_b_jwt>"
```

Both JWTs MUST share the same `wid` (workspace). There is no workspace-switch
API yet — prepare membership offline or use fixture mode for isolation cases.

## Golden schema

Common fields:

| Field | Meaning |
|-------|---------|
| `id` | Stable case id |
| `theme` | `retrieval` \| `tenant_isolation` |
| `mode_hint` | `fixture` \| `live` \| `either` |
| `surface` | e.g. `GET /ai/test-search` |
| `skip_if_modes` | optional list of modes to skip |

**Retrieval** extras:

- `query_text`
- `expect_content_markers` — substrings that should appear in hit text (preferred over hard-coded UUIDs)
- `expect_min_hits` — optional int
- `fixture_ref` — filename under `evals/fixtures/` for fixture mode
- `seed` — optional live seed: `{ "title", "content", "is_private", "wait_embed_sec" }`

**Tenant isolation** extras:

- `actor` — which token: `a` \| `b` (default `b` for deny cases)
- `expect_no_content_markers` — markers that must **not** appear for the actor
- `fixture_ref` — recorded search response for fixture mode
- `forged_workspace_probe` — if true, live mode sends an extra body field; results must still be JWT-scoped (Pydantic ignores unknown fields; workspace never taken from body)

**Agent trajectories** (Tier 1 / 8X.2.3 — schema reserved, not scored in Tier 0):

- `forbidden_tools`, `required_tools`, `sequence_mode` (`exact` \| `subset`)

## Seed / fixture ID law

- Do **not** hard-code `note_id` / `chunk_id` that only exist in one environment.
- Prefer `expect_content_markers` + live `seed`, or `fixture_ref` recorded hits.
- Document any seed script steps here when added.

## Latest recorded run

| When | Mode | Target | Result |
|------|------|--------|--------|
| 2026-09-06 | fixture | n/a | **PASS: 15/15** |
| 2026-09-06 | live + `--seed-live` | `http://127.0.0.1` | **PASS: 8/8** (7 skipped: fixture-only / need `--token-b`) |

Target C-gate: ≥80% on the retrieval + tenant set used for hire docs. Record the
honest `PASS: X/Y` even when below 100%.

## Post-C-gate (not this harness)

Langfuse-native datasets/experiments preferred for judges; optional recall@k /
faithfulness are Tier 2 / nightly. Do not replace this golden CLI.
