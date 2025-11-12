#!/usr/bin/env bash
set -euo pipefail

APP_MODULE=${APP_MODULE:-"app.main:app"}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8080"}
WORKERS=${WORKERS:-"4"}

exec uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"
