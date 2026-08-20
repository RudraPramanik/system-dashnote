#!/usr/bin/env bash
set -euo pipefail

# Apply Alembic migrations via the prod migrate service.
# Secrets come from compose env_file (.env on the VPS) — never hard-code them here.
COMPOSE_FILE="docker-compose.prod.yml"

docker compose -f "${COMPOSE_FILE}" run --rm migrate
