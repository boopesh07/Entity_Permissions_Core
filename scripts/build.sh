#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

IMAGE_NAME="${IMAGE_NAME:-omen-epr}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE_NAME="${IMAGE_REGISTRY:-}${IMAGE_NAME}:${IMAGE_TAG}"
SKIP_TESTS="${SKIP_TESTS:-false}"

if [[ "${SKIP_TESTS}" != "true" ]]; then
  echo "Running test suite..."
  .venv/bin/python -m pytest -vv
fi

echo "Building Docker image ${FULL_IMAGE_NAME}"
docker build -t "${FULL_IMAGE_NAME}" -f Dockerfile .
