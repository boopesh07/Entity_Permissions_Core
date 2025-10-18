#!/usr/bin/env bash
set -euo pipefail

echo "Deploy script started."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

ENV_FILE="${ENV_FILE:-.env}"
if [[ -f "${ENV_FILE}" ]]; then
  echo "Loading environment from ${ENV_FILE}"
  # shellcheck disable=SC1090
  set -a && source "${ENV_FILE}" && set +a
fi

AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
ECR_REPOSITORY="${ECR_REPOSITORY:?ECR_REPOSITORY env var required}"
ECS_CLUSTER="${ECS_CLUSTER:?ECS_CLUSTER env var required}"
ECS_SERVICE="${ECS_SERVICE:?ECS_SERVICE env var required}"
TASK_FAMILY="${TASK_FAMILY:-omen-epr}"
CONTAINER_NAME="${CONTAINER_NAME:-omen-epr}"
TASK_CPU="${TASK_CPU:-512}"
TASK_MEMORY="${TASK_MEMORY:-1024}"
IMAGE_NAME="${IMAGE_NAME:-omen-epr}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
SKIP_BUILD="${SKIP_BUILD:-false}"
EXECUTION_ROLE_ARN="${EXECUTION_ROLE_ARN:?EXECUTION_ROLE_ARN env var required}"
TASK_ROLE_ARN="${TASK_ROLE_ARN:?TASK_ROLE_ARN env var required}"
CLOUDWATCH_LOG_GROUP="${CLOUDWATCH_LOG_GROUP:-/ecs/${TASK_FAMILY}}"
CLOUDWATCH_STREAM_PREFIX="${CLOUDWATCH_STREAM_PREFIX:-ecs}"
EPR_ENVIRONMENT="${EPR_ENVIRONMENT:-production}"
EPR_DATABASE_URL="${EPR_DATABASE_URL:?EPR_DATABASE_URL env var required}"
EPR_LOG_LEVEL="${EPR_LOG_LEVEL:-INFO}"
EPR_LOG_JSON="${EPR_LOG_JSON:-true}"
EPR_SQL_ECHO="${EPR_SQL_ECHO:-false}"
ECS_LAUNCH_TYPE="${ECS_LAUNCH_TYPE:-FARGATE}"
ECS_PLATFORM_VERSION="${ECS_PLATFORM_VERSION:-LATEST}"
DESIRED_COUNT="${DESIRED_COUNT:-1}"
ECS_ASSIGN_PUBLIC_IP="${ECS_ASSIGN_PUBLIC_IP:-ENABLED}"
ECS_SUBNET_IDS="${ECS_SUBNET_IDS:-}"
ECS_SECURITY_GROUP_IDS="${ECS_SECURITY_GROUP_IDS:-}"
DEFAULT_SKIP_TESTS="${DEFAULT_SKIP_TESTS:-true}"

if [[ -z "${AWS_ACCOUNT_ID}" ]]; then
  echo "Deriving AWS account ID via STS"
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query 'Account' --output text)"
fi

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_REGION}"
export AWS_ACCOUNT_ID ECR_REPOSITORY IMAGE_NAME IMAGE_TAG

if [[ "${SKIP_BUILD}" != "true" ]]; then
  echo "Invoking build script for image ${IMAGE_URI}"
  SKIP_TESTS_VALUE="${SKIP_TESTS:-${DEFAULT_SKIP_TESTS}}"
  IMAGE_TAG="${IMAGE_TAG}" IMAGE_NAME="${IMAGE_NAME}" \
    ECR_REPOSITORY="${ECR_REPOSITORY}" AWS_REGION="${AWS_REGION}" AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}" \
    SKIP_TESTS="${SKIP_TESTS_VALUE}" \
    ./scripts/build.sh
else
  echo "SKIP_BUILD=true; assuming image ${IMAGE_URI} already exists"
fi

TEMPLATE_PATH="${PROJECT_ROOT}/infra/ecs-task-def.json.template"
if [[ ! -f "${TEMPLATE_PATH}" ]]; then
  echo "ERROR: Task definition template not found at ${TEMPLATE_PATH}" >&2
  exit 1
fi

RENDERED_TASK_DEF="$(mktemp "${TMPDIR:-/tmp}/ecs-task-def.XXXXXX")"
cleanup() {
  rm -f "${RENDERED_TASK_DEF}"
}
trap cleanup EXIT

export TEMPLATE_PATH RENDERED_TASK_DEF
export TASK_FAMILY CONTAINER_NAME IMAGE_URI EXECUTION_ROLE_ARN TASK_ROLE_ARN TASK_CPU TASK_MEMORY
export EPR_ENVIRONMENT EPR_DATABASE_URL EPR_LOG_LEVEL EPR_LOG_JSON EPR_SQL_ECHO AWS_REGION
export CLOUDWATCH_LOG_GROUP CLOUDWATCH_STREAM_PREFIX

python - <<'PY'
import os
from pathlib import Path

template_path = Path(os.environ["TEMPLATE_PATH"])
rendered_path = Path(os.environ["RENDERED_TASK_DEF"])

required_env = [
    "TASK_FAMILY",
    "CONTAINER_NAME",
    "IMAGE_URI",
    "EXECUTION_ROLE_ARN",
    "TASK_ROLE_ARN",
    "TASK_CPU",
    "TASK_MEMORY",
    "EPR_ENVIRONMENT",
    "EPR_DATABASE_URL",
    "EPR_LOG_LEVEL",
    "EPR_LOG_JSON",
    "EPR_SQL_ECHO",
    "AWS_REGION",
    "CLOUDWATCH_LOG_GROUP",
    "CLOUDWATCH_STREAM_PREFIX",
]
missing = [name for name in required_env if not os.environ.get(name)]
if missing:
    raise SystemExit(f"Missing env vars: {', '.join(missing)}")

replacements = {
    "TASK_FAMILY": os.environ["TASK_FAMILY"],
    "CONTAINER_NAME": os.environ["CONTAINER_NAME"],
    "IMAGE_URI": os.environ["IMAGE_URI"],
    "EXECUTION_ROLE_ARN": os.environ["EXECUTION_ROLE_ARN"],
    "TASK_ROLE_ARN": os.environ["TASK_ROLE_ARN"],
    "TASK_CPU": os.environ["TASK_CPU"],
    "TASK_MEMORY": os.environ["TASK_MEMORY"],
    "EPR_ENVIRONMENT": os.environ["EPR_ENVIRONMENT"],
    "EPR_DATABASE_URL": os.environ["EPR_DATABASE_URL"],
    "EPR_LOG_LEVEL": os.environ["EPR_LOG_LEVEL"],
    "EPR_LOG_JSON": os.environ["EPR_LOG_JSON"],
    "EPR_SQL_ECHO": os.environ["EPR_SQL_ECHO"],
    "AWS_REGION": os.environ["AWS_REGION"],
    "CLOUDWATCH_LOG_GROUP": os.environ["CLOUDWATCH_LOG_GROUP"],
    "CLOUDWATCH_STREAM_PREFIX": os.environ["CLOUDWATCH_STREAM_PREFIX"],
}

contents = template_path.read_text()
for key, value in replacements.items():
    contents = contents.replace(f"<{key}>", value)

rendered_path.write_text(contents)
PY

TASK_DEF_ARN=$(aws ecs register-task-definition --cli-input-json "file://${RENDERED_TASK_DEF}" --query 'taskDefinition.taskDefinitionArn' --output text)
echo "Registered task definition: ${TASK_DEF_ARN}"

SERVICE_STATUS=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" --services "${ECS_SERVICE}" --query 'services[0].status' --output text 2>/dev/null | tr -d '\r')
if [[ "${SERVICE_STATUS}" == "ACTIVE" ]]; then
  echo "Updating existing ECS service ${ECS_SERVICE}"
  aws ecs update-service \
    --cluster "${ECS_CLUSTER}" \
    --service "${ECS_SERVICE}" \
    --task-definition "${TASK_DEF_ARN}" \
    --desired-count "${DESIRED_COUNT}" \
    --force-new-deployment \
    --output text >/dev/null
else
  echo "Creating ECS service ${ECS_SERVICE}"
  if [[ -z "${ECS_SUBNET_IDS}" || -z "${ECS_SECURITY_GROUP_IDS}" ]]; then
    echo "ERROR: ECS_SUBNET_IDS and ECS_SECURITY_GROUP_IDS are required to create a new service." >&2
    exit 1
  fi

  export ECS_SUBNET_IDS ECS_SECURITY_GROUP_IDS ECS_ASSIGN_PUBLIC_IP
  NETWORK_CONFIGURATION=$(python - <<'PY'
import json
import os
import sys

subnets = [s.strip() for s in os.environ["ECS_SUBNET_IDS"].split(",") if s.strip()]
security_groups = [s.strip() for s in os.environ["ECS_SECURITY_GROUP_IDS"].split(",") if s.strip()]

if not subnets or not security_groups:
    sys.stderr.write("ERROR: ECS_SUBNET_IDS and ECS_SECURITY_GROUP_IDS must contain at least one value.\n")
    raise SystemExit(1)

assign_public_ip = os.environ.get("ECS_ASSIGN_PUBLIC_IP", "ENABLED")

payload = f"awsvpcConfiguration={{subnets={json.dumps(subnets)},securityGroups={json.dumps(security_groups)},assignPublicIp=\"{assign_public_ip}\"}}"
print(payload)
PY
)

  ARGS=(
    --cluster "${ECS_CLUSTER}"
    --service-name "${ECS_SERVICE}"
    --task-definition "${TASK_DEF_ARN}"
    --desired-count "${DESIRED_COUNT}"
    --launch-type "${ECS_LAUNCH_TYPE}"
    --platform-version "${ECS_PLATFORM_VERSION}"
    --network-configuration "${NETWORK_CONFIGURATION}"
  )

  if [[ "${ECS_ENABLE_EXECUTE_COMMAND:-false}" == "true" ]]; then
    ARGS+=(--enable-execute-command)
  fi
  aws ecs create-service "${ARGS[@]}" >/dev/null
  echo "Service ${ECS_SERVICE} created."
fi

echo "Deployment complete. Track rollout in ECS console."
