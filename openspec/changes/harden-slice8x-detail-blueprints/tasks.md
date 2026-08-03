## 1. Harden slice8_ci.md

- [ ] 1.1 Update Architecture Law: Dockerfile parity for Python + apt (match current `python:3.12-slim` / `libmagic1`); reject any 3.11-forever wording; keep no-prod-secrets / no-deploy scope
- [ ] 1.2 Expand 8X.1.0 inventory checklist (conftest setdefaults/stubs, pytest.ini, Dockerfile base/apt/requirements, CI requirements file choice, pytest baseline, forbidden secrets, service-container need verdict)
- [ ] 1.3 Update 8X.1.1–8X.1.2: recommend `PYTHONPATH: src`, align env to conftest (do not copy wrong credentials from `new.md`), service containers only per inventory, failure-category playbook
- [ ] 1.4 Sanity-check overview/checklist still keep 3.12 aligned with Dockerfile and parent links intact

## 2. Harden slice8_eval.md

- [ ] 2.1 Expand 8X.2.0 schema/law: fixture vs live modes; trajectory fields (`forbidden_tools`, `required_tools`, `sequence_mode`); seed-or-fixture ID strategy; evals import/`PYTHONPATH` docs
- [ ] 2.2 Update 8X.2.1 tenant cases: dual-token or fixture path so isolation is automatable
- [ ] 2.3 Update 8X.2.2–8X.2.3 runner/trajectory prompts to score against the locked schema fields
- [ ] 2.4 Update 8X.2.4: PR CI only fixture/deterministic; live operator/nightly; honest pass-rate docs unchanged in spirit

## 3. Harden slice8_hitl.md

- [ ] 3.1 Update Architecture Law: LangGraph version/API check; checkpointer = pending state (not automation `pending_actions` table); lock `approval_required` JSON fields; prefer emit-then-close SSE + resume reconnect
- [ ] 3.2 Update 8X.3.1–8X.3.2 prompts for interrupt API discipline, event shape, and ordering vs `tool_start`/`tool_end`
- [ ] 3.3 Update 8X.3.3 resume: mandatory workspace ownership validation on `thread_id` before mutate
- [ ] 3.4 Update 8X.3.4 gate text if needed so smoke/tests cover approve/reject under the new contract

## 4. Cross-check and sync

- [ ] 4.1 Skim `slice8_X.md` for contradictions with hardened laws; fix only if a line conflicts (no structural rewrite)
- [ ] 4.2 Ensure `new.md` is not linked as source of truth from the three blueprints (scratch/review only)
- [ ] 4.3 Sync delta specs into main `openspec/specs/slice8x-*-blueprint/` when applying/archiving this change (or via `/opsx:sync` / archive flow)
