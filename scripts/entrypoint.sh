#!/usr/bin/env bash
set -euo pipefail

APP_MODULE=${APP_MODULE:-"app.main:app"}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8080"}
WORKERS=${WORKERS:-"4"}
RUN_MIGRATIONS=${RUN_MIGRATIONS:-"true"}

if [[ "${RUN_MIGRATIONS}" == "true" ]]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

exec uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"
