Dependency Direction Law (Never Violate)
src/shared/  ←  imported by ai/, worker/, domain modules. Imports NOTHING.
src/ai/      ←  imports from src/shared/ only. Never src/notes/, src/worker/.
src/worker/  ←  imports from src/ai/ and src/shared/. Never FastAPI/HTTP logic.
src/notes/   ←  calls src/ai/services/ via service interface only.
src/files/   ←  same pattern as src/notes/.
One sentence: shared ← ai ← worker and shared ← src modules → ai/services
Tools → services → repositories. Never shortcut this chain.

Never Rewrite — Only Append
docker-compose.yml  →  append new services only
requirements.txt    →  append new packages only, grouped by slice comment
settings.py         →  append new fields only, grouped by slice comment
.env                →  append new vars only, grouped by slice comment
Dockerfile          →  evolve only if a new system package is truly needed



Package Install Discipline
Install a package ONLY when writing the code that imports it.
Add it to requirements.txt immediately under # --- AI requirements --- or #------worker requirements ---
Never install speculatively.

<!--  -->

ARCHITECTURE LAW — DashNoteSystem. Memorise and enforce in ALL generated code.

LAYER STRUCTURE (all inside src/):
  src/shared/    → contracts, events, schemas. Imports NOTHING from other layers.
  src/ai/        → AI orchestration. No HTTP. No FastAPI.
  src/worker/    → ARQ background jobs. No HTTP. No FastAPI.
  src/notes/     → existing domain. Minimal additions only.

AI MODULE IMPORT LAW — src/ai/* may ONLY import from:
  - src.shared.*
  - src.config.settings
  - src.core.redis.*
  - stdlib + third-party packages

AI MODULES MUST NEVER IMPORT(exception allowed for need):
  - FastAPI, Request, Response, APIRouter, Depends, HTTPException
  - SQLAlchemy sessions or any repository class
  - src.notes.*, src.files.*, src.auth.*, src.workspaces.*
  - src.worker.*

WORKER MODULES MUST NEVER IMPORT(exception allowed for need)::
  - FastAPI or any HTTP-related module
  - Domain repositories directly

ROUTER LAW:
  - Do not refactor, reorder, or rewrite existing router logic
  - Only append minimal enqueue blocks after successful DB commits
  - Never move, rename, or delete existing route functions

INFRA LAW:
  - Do not create additional Dockerfiles or docker-compose files
  - Do not create requirements.worker.txt or requirements.api.txt
  - All changes go into the existing Dockerfile and requirements.txt


PYDANTIC LAW:
  - Use Pydantic V2 throughout — BaseModel, ConfigDict, model_validator
  - All shared data models use ConfigDict(frozen=True)
  - Use Python 3.11+ type hints: str | None not Optional[str]

Acknowledge these laws before writing any code.