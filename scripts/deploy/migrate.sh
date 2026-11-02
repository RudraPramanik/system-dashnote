#!/usr/bin/env bash
set -euo pipefail

# Apply Alembic migrations via the prod migrate service.
# Secrets come from compose env_file (.env on the VPS) — never hard-code them here.
COMPOSE_FILE="docker-compose.prod.yml"

if [[ "${COMPOSE_PROFILES:-}" == *"onbox-db"* ]] || [[ "${ONBOX_DB:-}" == "1" ]]; then
  export COMPOSE_PROFILES="${COMPOSE_PROFILES:+$COMPOSE_PROFILES,}onbox-db"
  docker compose -f "${COMPOSE_FILE}" --profile onbox-db up -d postgres
  attempt=1
  while [ "${attempt}" -le 30 ]; do
    if docker compose -f "${COMPOSE_FILE}" --profile onbox-db ps postgres 2>/dev/null | grep -qi "healthy"; then
      break
    fi
    if [ "${attempt}" -eq 30 ]; then
      echo "ERROR: postgres not healthy before migrate" >&2
      exit 1
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
fi

docker compose -f "${COMPOSE_FILE}" run --rm migrate
