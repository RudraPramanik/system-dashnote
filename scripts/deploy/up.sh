#!/usr/bin/env bash
set -euo pipefail

# Bring up prod compute: optional on-box postgres, api first (wait healthy), then worker + nginx.
# Secrets come from compose env_file (.env on the VPS) — never hard-code them here.
# Set COMPOSE_PROFILES=onbox-db (or export it in .env via compose) when using on-VPS Postgres.
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-30}"
SLEEP_SECS="${SLEEP_SECS:-2}"

if [[ "${COMPOSE_PROFILES:-}" == *"onbox-db"* ]] || [[ "${ONBOX_DB:-}" == "1" ]]; then
  export COMPOSE_PROFILES="${COMPOSE_PROFILES:+$COMPOSE_PROFILES,}onbox-db"
  echo "Starting on-box postgres (profile onbox-db)..."
  docker compose -f "${COMPOSE_FILE}" --profile onbox-db up -d postgres
  attempt=1
  while [ "${attempt}" -le 30 ]; do
    if docker compose -f "${COMPOSE_FILE}" --profile onbox-db ps postgres 2>/dev/null | grep -qi "healthy"; then
      echo "postgres is healthy"
      break
    fi
    if [ "${attempt}" -eq 30 ]; then
      echo "ERROR: postgres did not become healthy" >&2
      docker compose -f "${COMPOSE_FILE}" --profile onbox-db ps postgres >&2 || true
      exit 1
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
fi

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
