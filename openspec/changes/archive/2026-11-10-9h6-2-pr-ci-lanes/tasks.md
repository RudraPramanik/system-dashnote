## 1. Confirm PR coverage

- [x] 1.1 Verify `tests/ai/test_harness_fixture_themes.py` still exists with the four designated theme checks and is not listed under `.github/workflows/ci.yml` `--ignore` paths
- [x] 1.2 Confirm thin CI’s merge-blocking test step remains `python -m pytest -q` (plus fixture evals) with no live LLM / VPS / SSH secrets required for a green harness theme run

## 2. Document PR versus nightly lanes

- [x] 2.1 Annotate `.github/workflows/ci.yml` header/comments: name `tests/ai/test_harness_fixture_themes.py` as Blueprint 9 harness grade proof on the blocking pytest lane; state that live jailbreak / LLM-as-judge / live-mode evals are out of this workflow and non-blocking for merge
- [x] 2.2 Add a short operator note in `evals/README.md` that Blueprint 9 harness themes ride PR pytest (`python -m pytest tests/ai/test_harness_fixture_themes.py -q` focused; full CI via thin pytest job) and that live red-team / judges stay operator or nightly and non-blocking
- [x] 2.3 If `docs/documentation/blueprint/slice9_eval.md` or `docs/documentation/blueprint9.md` still reads as if the CI split is unfinished, add a thin cross-link or one-paragraph status pointing at the PR pytest lane — do not claim security B+, cost B+, or orchestration A- (9H.6.3)

## 3. Guardrails

- [x] 3.1 Do not add a merge-required nightly GitHub Actions job, provider API keys to PR CI, Alembic, `docker-compose.yml` edits, or Qdrant (`notes_chunks` / `files_chunks`) changes. Do not implement live jailbreak suites. Keep `/ai/chat*` and `/ai/agent*` both mounted

## 4. Proof

- [x] 4.1 Run `python -m pytest tests/ai/test_harness_fixture_themes.py -q` and confirm all four themes pass without a live LLM key
- [x] 4.2 In the apply summary, state the PR blocking vehicle (thin CI pytest), the focused catalog command, and that any mentioned live/judge lane is labeled non-blocking
