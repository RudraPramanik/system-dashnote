# DashNoteSystem

Multi-tenant notes backend: **FastAPI**, **PostgreSQL**, **Redis**, **Qdrant**, **ARQ worker**. AI features include embeddings, RBAC-aware semantic search, RAG chat (JSON + SSE), and a LangGraph workspace agent.

## Quick start

```powershell
docker compose up -d --build
curl.exe -sS http://127.0.0.1/health
```

Migrations run via the `migrate` service on startup. See [alembic/README](alembic/README) for manual Alembic commands.

## Documentation

- [System workflow & routing](docs/documentation/system.md)
- [AI architecture](docs/documentation/ai.md)
- [UML diagrams](docs/uml/diagrams.md)
