#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

REVISION="${1:-head}"

echo "Applying database migrations up to ${REVISION}"
.venv/bin/alembic upgrade "${REVISION}"
