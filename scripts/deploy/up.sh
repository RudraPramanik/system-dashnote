#!/usr/bin/env bash
set -euo pipefail

# Bring up prod compute: api first (wait healthy), then worker + nginx.
# Secrets come from compose env_file (.env on the VPS) — never hard-code them here.
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-30}"
SLEEP_SECS="${SLEEP_SECS:-2}"

docker compose -f "${COMPOSE_FILE}" up -d api

echo "Waiting for API health..."
attempt=1
while [ "${attempt}" -le "${MAX_ATTEMPTS}" ]; do
  if docker compose -f "${COMPOSE_FILE}" ps api 2>/dev/null | grep -qi "healthy"; then
    echo "api is healthy"
    break
  fi
  if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "edge health OK at ${HEALTH_URL}"
    break
  fi
  if [ "${attempt}" -eq "${MAX_ATTEMPTS}" ]; then
    echo "ERROR: api did not become healthy within $((MAX_ATTEMPTS * SLEEP_SECS))s" >&2
    docker compose -f "${COMPOSE_FILE}" ps api >&2 || true
    exit 1
  fi
  sleep "${SLEEP_SECS}"
  attempt=$((attempt + 1))
done

docker compose -f "${COMPOSE_FILE}" up -d worker nginx

echo "api, worker, and nginx are up."
echo "Optional observability: docker compose -f ${COMPOSE_FILE} --profile observability up -d prometheus"
