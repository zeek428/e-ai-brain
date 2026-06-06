#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export READINESS_API_BASE_URL="${READINESS_API_BASE_URL:-http://localhost:8000}"
export READINESS_WEB_BASE_URL="${READINESS_WEB_BASE_URL:-http://localhost:5173}"

if [[ -z "${READINESS_DOCKER_BIN:-}" && -x "/Applications/Docker.app/Contents/Resources/bin/docker" ]]; then
  export READINESS_DOCKER_BIN="/Applications/Docker.app/Contents/Resources/bin/docker"
fi

exec "${REPO_ROOT}/scripts/production_readiness_check.py" \
  --rebuild \
  --web-smoke \
  --api-base-url "${READINESS_API_BASE_URL}" \
  --web-base-url "${READINESS_WEB_BASE_URL}"
