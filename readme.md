project-architecture/
├── alembic/
├── src/
│   ├── main.py
│   ├── config.py              # global settings (env, flags)
│
│   ├── core/                  # cross-cutting infrastructure
│   │   ├── database/
│   │   │   ├── base.py        # declarative base
│   │   │   ├── session.py     # async session + dependency
│   │   │   ├── mixins.py      # tenant, timestamps, soft delete
│   │   │   └── utils.py       # tenant-safe helpers
│   │   │
│   │   ├── cache/
│   │   │   ├── redis.py       # redis client
│   │   │   ├── keys.py        # cache key builders
│   │   │   └── decorators.py  # @cached helpers
│   │   │
│   │   ├── events/
│   │   │   ├── base.py        # Event interface
│   │   │   ├── dispatcher.py  # emit / publish
│   │   │   └── handlers.py    # async consumers
│   │   │
│   │   ├── middleware/
│   │   │   ├── auth.py        # auth context
│   │   │   ├── tenant.py      # tenant enforcement
│   │   │   ├── logging.py     # request logs
│   │   │   └── rate_limit.py
│   │   │
│   │   ├── security/
│   │   │   ├── jwt.py
│   │   │   ├── password.py
│   │   │   └── permissions.py
│   │   │
│   │   ├── storage/
│   │   │   ├── s3.py
│   │   │   └── interfaces.py
│   │   │
│   │   ├── observability/
│   │   │   ├── logging.py
│   │   │   ├── metrics.py
│   │   │   └── tracing.py
│   │   │
│   │   └── exceptions.py
│
│   ├── auth/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── constants.py
│   │   └── exceptions.py
│
│   ├── workspaces/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── exceptions.py
│
│   ├── notebooks/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── events.py
│
│   ├── pages/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── versioning.py
│
│   ├── files/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── ingestion.py
│
│   ├── decisions/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── service.py
│
│   ├── search/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── text.py
│   │   └── semantic.py
│
│   ├── ai/
│   │   ├── tasks.py           # background jobs
│   │   ├── embeddings.py
│   │   └── clients.py
│
│   ├── workers/
│   │   ├── worker.py          # entrypoint
│   │   └── registry.py
│
│   └── tests/
│       ├── auth/
│       ├── notebooks/
│       └── pages/
│
├── logging.ini
├── alembic.ini
├── requirements/
└── .env
