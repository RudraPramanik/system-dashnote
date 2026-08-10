## 1. Inventory (8X.1.0)

- [x] 1.1 Read `tests/conftest.py` and list every `os.environ.setdefault`, magic/other stubs, and whether fixtures need live DB/Redis
- [x] 1.2 Record `pytest.ini` (`pythonpath`, `testpaths`, `asyncio_mode`, `addopts`) and Dockerfile `FROM`, apt packages, requirements file, WORKDIR/PYTHONPATH
- [x] 1.3 Decide which requirements file CI pip-installs (prefer Dockerfile path) and service-container verdict: READY-without-services | NEED postgres | NEED redis | NEED both
- [x] 1.4 Run or cite `python -m pytest -q`; if largely red, STOP with BLOCKED or document an explicit allowlist
- [x] 1.5 Write inventory report with forbidden secrets list and READY | BLOCKED verdict — do not create `ci.yml` yet

## 2. Workflow skeleton (8X.1.1)

- [x] 2.1 Create `.github/workflows/ci.yml` with `pull_request` and `push` to default branch triggers
- [x] 2.2 Add `test` job: checkout, `setup-python` matching Dockerfile, optional apt stub, pip install inventory-chosen requirements, `PYTHONPATH: src`, pytest step (may still fail)
- [x] 2.3 Add `build` job with `needs: [test]` that runs `docker build` — no SSH, no prod secrets, no deploy jobs
- [x] 2.4 Add `services:` only if inventory said NEED_* and align env to conftest setdefaults when listing credentials

## 3. Test job green (8X.1.2)

- [x] 3.1 Align job `env` with conftest/inventory placeholders (no invented prod credentials; no required live LLM/Qdrant keys)
- [x] 3.2 Install Dockerfile apt packages (e.g. `libmagic1`) and confirm pip install path matches inventory
- [x] 3.3 Iterate on Actions failures using smallest category fix (imports, apt, Settings env, DB, missing packages) until pytest is green or only allowlisted failures remain
- [x] 3.4 Confirm `docker-compose.yml` was not broken for local full-stack use

## 4. Build gate + tracker (8X.1.3)

- [x] 4.1 Confirm `build` job succeeds after `test` without BuildKit LLM secrets
- [x] 4.2 Mark `docs/documentation/production.md` step 7P.7 CI as done
- [x] 4.3 Optional: short note on running pytest locally before push (README or docs only if needed)
