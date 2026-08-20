#!/usr/bin/env bash
set -euo pipefail

# Hard health check at the published nginx edge.
# GET /health requires Postgres + Redis; Qdrant/LLM soft failures must not fail this gate.
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health}"

body="$(curl -sf "${HEALTH_URL}")" || {
  echo "ERROR: health request failed: ${HEALTH_URL}" >&2
  exit 1
}

if command -v jq >/dev/null 2>&1; then
  printf '%s\n' "${body}" | jq .
  if ! printf '%s' "${body}" | jq -e '
    (.status == "ok")
    or (.status == "healthy")
    or (.ok == true)
  ' >/dev/null 2>&1; then
    echo "ERROR: health payload not ok: ${body}" >&2
    exit 1
  fi
else
  printf '%s\n' "${body}"
  if ! printf '%s' "${body}" | grep -Eqi '"status"[[:space:]]*:[[:space:]]*"(ok|healthy)"|"ok"[[:space:]]*:[[:space:]]*true'; then
    echo "ERROR: health body missing ok/healthy status (install jq for stricter checks): ${body}" >&2
    exit 1
  fi
fi

echo "health-check OK"
