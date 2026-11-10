## 1. Verify prerequisite theme sources

- [x] 1.1 Confirm the four source behaviors still exist and are executable without a live LLM key: `tests/ai/test_harness_trust.py::test_search_uses_harness_workspace_not_foreign`, `tests/ai/test_harness_policy.py::test_forbidden_update_does_not_commit`, `tests/ai/test_injection_hygiene.py` poisoned checks (`test_poisoned_content_cannot_retarget_workspace` and `test_poisoned_content_cannot_skip_hitl`), `tests/ai/test_harness_budget_refusal.py::test_chat_over_budget_is_429_and_skips_the_model`. If any behavior is missing, stop and name the earlier 9H substep — do not stub a green theme

## 2. Grade-proof catalog

- [x] 2.1 Add `tests/ai/test_harness_fixture_themes.py` with a module docstring that maps each Blueprint 9H.6.1 theme → designated check name → source test, and states that pytest (not `evals/golden/`) is the fixture vehicle for these harness themes
- [x] 2.2 Implement exactly four designated checks: `test_theme_invented_workspace_not_used`, `test_theme_forbidden_role_does_not_commit`, `test_theme_poisoned_retrieval_cannot_retarget_or_skip_hitl`, `test_theme_budget_exceeded_skips_model`. Back them by calling/reusing the existing source assertions (import existing test callables or shared helpers). Do not duplicate the same theme as a new `evals/golden/` JSONL case
- [x] 2.3 Ensure the poisoned theme is a single nodeid that covers retarget and/or skip-HITL as locked in design (no commit without HITL; no cross-tenant call). Do not `pytest.skip` any theme for missing secrets
- [x] 2.4 Do not claim security B+, cost B+, or orchestration A-. Do not add a new GitHub workflow (9H.6.2). Do not edit `docker-compose.yml`, Alembic, or Qdrant (`notes_chunks` / `files_chunks`). Keep `/ai/chat*` and `/ai/agent*` both mounted

## 3. Proof

- [x] 3.1 Run `python -m pytest tests/ai/test_harness_fixture_themes.py -q` and confirm all four themes pass without a live LLM key
- [x] 3.2 In the apply summary, list the four theme → file/nodeid mappings so operators can find the grade-proof gate. Note that full PR CI already runs these via `python -m pytest -q`
