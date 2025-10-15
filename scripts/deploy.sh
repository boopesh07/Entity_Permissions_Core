#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

: "${AWS_REGION:?Environment variable AWS_REGION is required}"
: "${AWS_ACCOUNT_ID:?Environment variable AWS_ACCOUNT_ID is required}"
: "${ECR_REPOSITORY:?Environment variable ECR_REPOSITORY is required}"
: "${ECS_CLUSTER:?Environment variable ECS_CLUSTER is required}"
: "${ECS_SERVICE:?Environment variable ECS_SERVICE is required}"

IMAGE_NAME="${IMAGE_NAME:-omen-epr}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
LOCAL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
REMOTE_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "Building image ${LOCAL_IMAGE}"
IMAGE_NAME="${IMAGE_NAME}" IMAGE_TAG="${IMAGE_TAG}" ./scripts/build.sh

echo "Authenticating to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Tagging image ${LOCAL_IMAGE} -> ${REMOTE_IMAGE}"
docker tag "${LOCAL_IMAGE}" "${REMOTE_IMAGE}"

echo "Pushing image to ECR..."
docker push "${REMOTE_IMAGE}"

echo "Triggering ECS deployment..."
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --force-new-deployment \
  --region "${AWS_REGION}" \
  >/dev/null

echo "Deployment triggered successfully. Track rollout in ECS console."
