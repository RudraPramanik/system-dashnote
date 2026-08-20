# Slice 8X.1.0 — CI readiness inventory

**Date:** 2026-08-10  
**Change:** `add-thin-ci`  
**Verdict:** **READY** for 8X.1.1

---

## 1. `tests/conftest.py`

### `os.environ.setdefault`
| Name | Value |
|------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://dashuser:dashpass@127.0.0.1:5432/dashnotes` |
| `JWT_SECRET` | `pytest-jwt-secret-not-for-production` |

### Stubs
- **`magic`**: `_ensure_magic_stub()` installs a fake `magic` module with `from_buffer` → `application/octet-stream` so `core.storage.utils` imports without system libmagic (esp. Windows). On Ubuntu CI, real `libmagic1` + `python-magic` still match Dockerfile; stub is harmless if real magic is present first.

### Live DB/Redis in conftest?
- **No** live connections created in conftest.
- Autouse fixture `_reset_shared_redis_after_test` only calls `reset_async_redis_client()` after each test (clears process singleton). Does **not** require a live Redis server.

### Fixtures requiring live services?
- **No** — API tests use `sqlite+aiosqlite:///:memory:`; Redis tests use fakes/`AsyncMock`/`redis=None`.

---

## 2. `pytest.ini`

| Key | Value |
|-----|--------|
| `addopts` | `--import-mode=importlib` |
| `asyncio_mode` | `auto` |
| `asyncio_default_fixture_loop_scope` | `function` |
| `pythonpath` | `src` |
| `testpaths` | `tests` |

---

## 3. `Dockerfile`

| Item | Value |
|------|--------|
| `FROM` | `python:3.12-slim` |
| apt-get | `libmagic1` only |
| pip | `requirements/base.txt` |
| `WORKDIR` | `/app` |
| `PYTHONPATH` | not set in Dockerfile |
| `CMD` | `uvicorn src.main:app ...` |

---

## 4. Requirements — CI pip-install path

- **Dockerfile / image parity:** `requirements/base.txt` (includes `pytest`, `pytest-asyncio`, `python-magic`).
- **Test-only extra not in `base.txt`:** `aiosqlite` (present in root `requirements.txt`; used by sqlite in-memory API/pages tests).
- **CI install command:**  
  `pip install -r requirements/base.txt && pip install aiosqlite`  
  Do **not** invent a third requirements tree. Do **not** use root `requirements.txt` as primary (it includes build tooling and drifts from Dockerfile).

---

## 5. Service-container verdict

**READY-without-services**

Evidence:
- Multiple tests: `create_async_engine("sqlite+aiosqlite:///:memory:")` (`tests/auth`, `notebooks`, `notes`, `pages`).
- Redis: `_FakeRedis`, `AsyncMock`, or `redis=None` — no live `REDIS_URL` required.
- Conftest `DATABASE_URL` setdefault points at local Postgres **only as a Settings placeholder**; suite does not open that URL during the measured unit baseline.
- Do **not** add GitHub Actions postgres/redis `services:` unless a future test proves need.

---

## 6. Local pytest baseline

### Full suite (user site-packages, Python 3.13)
```
5 errors during collection (interrupted)
```
Root cause: `ModuleNotFoundError: No module named 'langgraph.prebuilt'` when importing `create_app` / `ai_routes.agent` (broken user-site namespace despite `pip show langgraph-prebuilt`).

Files blocked on collection:
- `tests/ai/test_agent_retry.py`
- `tests/auth/test_auth_tokens_api.py`
- `tests/notebooks/test_notebooks_api.py`
- `tests/notes/test_notes_rbac_api.py`
- `tests/supabase_smoke_test.py`

### Excluding those five (polluted user site)
```
92 passed, 1 failed (pages — later shown as JSONB/sqlite)
```

### Clean venv check (inventory + CI simulation)
```
python -m venv .ci-inv-venv
pip install -r requirements/base.txt aiosqlite
→ from langgraph.prebuilt import ToolNode  # OK
→ import aiosqlite  # OK
→ python -m pytest -q
   93 passed, 4 failed
```
Collection failure on user site is **local env pollution**. Fresh install restores agent imports.

### Explicit allowlist (JSONB vs sqlite)
These four use `sqlite+aiosqlite:///:memory:` + `Base.metadata.create_all`, which fails compiling Postgres `JSONB` (`files.tags`):

- `tests/auth/test_auth_tokens_api.py`
- `tests/notebooks/test_notebooks_api.py`
- `tests/notes/test_notes_rbac_api.py`
- `tests/pages/test_versioning.py`

**CI:** `--ignore` those four until Postgres-backed fixtures (or a PG service + test rewrite) exist. Not mass-skip of the suite.

`tests/supabase_smoke_test.py`: no `test_*` functions (manual `__main__` only); collection-only, not executed.

### Allowlisted CI simulation
```
93 passed (with the four --ignore flags above)
```

---

## 7. Secrets that MUST NOT be required CI secrets

- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `NVIDIA_NIM_API_KEY` / `NVIDIA_API_KEY`
- `QDRANT_URL`, `QDRANT_API_KEY`
- Production `DATABASE_URL` / Supabase / Upstash / Redis Cloud URLs
- VPS SSH keys, deploy tokens, registry prod creds
- R2 / MinIO production credentials
- Langfuse / Grafana Cloud tokens

Safe job env (optional explicit; conftest setdefaults cover unset):
- `DATABASE_URL`: same placeholder as conftest (or leave unset and rely on setdefault)
- `JWT_SECRET`: `pytest-jwt-secret-not-for-production`
- `PYTHONPATH`: `src`
- Optional: `REDIS_ENABLED=false` if Settings import ever hard-requires Redis (not required by current baseline)

---

## 8. Verdict

| Gate | Result |
|------|--------|
| Inventory complete | yes |
| Service containers | READY-without-services |
| CI requirements | `base.txt` + `aiosqlite` |
| Python / apt | 3.12 / `libmagic1` |
| Local suite largely red? | **No** — 93 green with explicit JSONB/sqlite allowlist (4 files) |
| **READY for 8X.1.1?** | **READY** |

**Default branch note:** `origin` HEAD is `stage` (also `main`, `production` exist). Workflow `push.branches` should include at least `stage` and `main`.

**Cleanup:** remove local `.ci-inv-venv` after inventory (not committed).
