# Deployment Guide

This guide explains how to deploy the Entity & Permissions Core service with the audit worker.

## Architecture Overview

The deployment uses a **multi-container ECS task** with:
- **API Container** (essential): FastAPI web service on port 8080
- **Audit Worker Container** (non-essential): SQS consumer for audit events

Both containers run in the same ECS task, sharing:
- Network namespace
- Same Docker image
- Database connection
- Log group

## Prerequisites

1. **AWS Resources:**
   - ECS Cluster
   - ECR Repository
   - RDS PostgreSQL Database
   - Upstash Redis instance
   - SNS Topic for document vault events
   - SQS Queue for audit events (subscribed to audit SNS topic)
   - IAM Roles (execution role + task role with SQS/SNS permissions)
   - VPC with subnets and security groups

2. **Local Tools:**
   - Docker + buildx
   - AWS CLI v2
   - Python 3.12+ (for tests)

3. **AWS Credentials:**
   ```bash
   export AWS_PROFILE=your-profile
   # OR
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

## Environment Variables

Create a `.env` file or export these variables:

### Required Variables

```bash
# AWS Configuration
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="123456789012"  # Auto-detected if not provided

# ECR & ECS
export ECR_REPOSITORY="omen-epr"
export ECS_CLUSTER="omen-production"
export ECS_SERVICE="omen-epr-service"
export ECS_SUBNET_IDS="subnet-xxx,subnet-yyy"  # Comma-separated
export ECS_SECURITY_GROUP_IDS="sg-xxx"

# IAM Roles
export EXECUTION_ROLE_ARN="arn:aws:iam::123456789012:role/ecsTaskExecutionRole"
export TASK_ROLE_ARN="arn:aws:iam::123456789012:role/omenEprTaskRole"

# Database
export EPR_DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/epr_db"

# Redis (Upstash)
export EPR_REDIS_URL="https://your-redis.upstash.io"
export EPR_REDIS_TOKEN="your_redis_token"

# SNS Topic for Document Vault
export EPR_DOCUMENT_VAULT_TOPIC_ARN="arn:aws:sns:us-east-1:123456789012:epr-document-events"

# SQS Queue for Audit Worker
export EPR_AUDIT_SQS_URL="https://sqs.us-east-1.amazonaws.com/123456789012/epr-audit-events-queue"
```

### Optional Variables (with defaults)

```bash
# Task Configuration
export TASK_FAMILY="omen-epr"                   # Default: omen-epr
export CONTAINER_NAME="omen-epr"                # Default: omen-epr
export TASK_CPU="512"                           # Default: 512
export TASK_MEMORY="1024"                       # Default: 1024
export DESIRED_COUNT="1"                        # Default: 1

# Application Settings
export EPR_ENVIRONMENT="production"             # Default: production
export EPR_LOG_LEVEL="INFO"                     # Default: INFO
export EPR_LOG_JSON="true"                      # Default: true
export EPR_SQL_ECHO="false"                     # Default: false
export EPR_REDIS_CACHE_PREFIX="epr"             # Default: epr
export EPR_REDIS_CACHE_TTL="300"                # Default: 300 seconds

# Worker Configuration
export EPR_AUDIT_SQS_MAX_MESSAGES="5"           # Default: 5
export EPR_AUDIT_SQS_WAIT_TIME="20"             # Default: 20 seconds
export EPR_AUDIT_SQS_VISIBILITY_TIMEOUT="60"    # Default: 60 seconds

# Build Configuration
export IMAGE_TAG="$(date +%Y%m%d%H%M%S)"       # Default: timestamp
export SKIP_BUILD="false"                       # Set to "true" to skip build
export SKIP_TESTS="true"                        # Set to "false" to run tests before build

# Logging
export CLOUDWATCH_LOG_GROUP="/ecs/omen-epr"    # Default: /ecs/${TASK_FAMILY}
export CLOUDWATCH_STREAM_PREFIX="ecs"          # Default: ecs
```

## Deployment Steps

### 1. Quick Deploy (Full Pipeline)

```bash
# Deploy everything (build + push + register + update service)
./scripts/deploy.sh
```

This will:
1. Build and test the Docker image (unless `SKIP_TESTS=true`)
2. Push image to ECR
3. Render task definition with both API + worker containers
4. Register new task definition
5. Update (or create) ECS service

### 2. Deploy Without Rebuilding

If the image already exists in ECR:

```bash
SKIP_BUILD=true ./scripts/deploy.sh
```

### 3. Build Only (No Deployment)

```bash
./scripts/build.sh
```

### 4. Deploy Without Worker

If you want to deploy only the API without the audit worker, you have two options:

#### Option A: Leave `EPR_AUDIT_SQS_URL` empty
```bash
export EPR_AUDIT_SQS_URL=""
./scripts/deploy.sh
```

The worker container will start but immediately fail (won't affect API since it's non-essential).

#### Option B: Modify task definition template
Remove the `audit-worker` container definition from `infra/ecs-task-def.json.template`.

## Task Resource Allocation

The default configuration allocates:
- **Total Task:** 512 CPU units, 1024 MB memory
- **API Container:** Uses most resources (no explicit limits = remaining capacity)
- **Worker Container:** Lightweight (no explicit limits, shares remaining)

For high-volume audit ingestion, increase task resources:

```bash
export TASK_CPU="1024"    # 1 vCPU
export TASK_MEMORY="2048"  # 2 GB
```

## Monitoring Deployment

### Check Service Status

```bash
aws ecs describe-services \
  --cluster omen-production \
  --services omen-epr-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,TaskDef:taskDefinition}'
```

### View Container Logs

#### API Logs
```bash
aws logs tail /ecs/omen-epr --follow --filter-pattern "ecs"
```

#### Worker Logs
```bash
aws logs tail /ecs/omen-epr --follow --filter-pattern "worker"
```

### Check Task Health

```bash
# List running tasks
aws ecs list-tasks --cluster omen-production --service omen-epr-service

# Describe specific task
aws ecs describe-tasks --cluster omen-production --tasks <task-arn>
```

### Health Check Endpoint

```bash
# Via load balancer
curl https://your-api-endpoint.com/healthz

# Direct task IP (if in public subnet)
curl http://<task-public-ip>:8080/healthz
```

## Rollback Procedure

If deployment fails:

```bash
# List task definition revisions
aws ecs list-task-definitions --family-prefix omen-epr

# Roll back to previous version
aws ecs update-service \
  --cluster omen-production \
  --service omen-epr-service \
  --task-definition omen-epr:5  # Use previous revision number
```

## Troubleshooting

### Worker Not Processing Messages

1. **Check SQS Permissions:**
   ```bash
   # Verify task role has SQS permissions
   aws iam get-role-policy --role-name omenEprTaskRole --policy-name SQSAccess
   ```

2. **Check Worker Logs:**
   ```bash
   aws logs tail /ecs/omen-epr --follow --filter-pattern "audit_consumer"
   ```

3. **Verify SQS Queue:**
   ```bash
   aws sqs get-queue-attributes \
     --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/epr-audit-events-queue \
     --attribute-names ApproximateNumberOfMessages
   ```

### API Container Unhealthy

1. **Check application logs:**
   ```bash
   aws logs tail /ecs/omen-epr --follow --filter-pattern "ERROR"
   ```

2. **Test database connectivity:**
   ```bash
   # From within container
   aws ecs execute-command \
     --cluster omen-production \
     --task <task-id> \
     --container omen-epr \
     --interactive \
     --command "/bin/bash"
   ```

### Task Keeps Restarting

1. **Check stopped tasks:**
   ```bash
   aws ecs describe-tasks \
     --cluster omen-production \
     --tasks $(aws ecs list-tasks --cluster omen-production --desired-status STOPPED --max-items 5 --query 'taskArns[0]' --output text)
   ```

2. **Common issues:**
   - Missing environment variables
   - Database connection failure
   - Insufficient IAM permissions
   - Invalid Redis credentials

## Migration Path to Separate Worker Service

When ready to migrate to Option 1 (separate ECS service):

1. **Create worker-specific task definition:**
   ```bash
   # Copy and modify template
   cp infra/ecs-task-def.json.template infra/ecs-worker-task-def.json.template
   # Remove API container, keep only worker
   ```

2. **Deploy worker as separate service:**
   ```bash
   aws ecs create-service \
     --cluster omen-production \
     --service-name omen-epr-audit-worker \
     --task-definition omen-epr-worker \
     --desired-count 1 \
     --launch-type FARGATE
   ```

3. **Remove worker from main task definition:**
   - Edit `infra/ecs-task-def.json.template`
   - Remove `audit-worker` container definition
   - Redeploy main service

## Security Best Practices

1. **Use AWS Secrets Manager for sensitive values:**
   ```json
   {
     "name": "EPR_DATABASE_URL",
     "valueFrom": "arn:aws:secretsmanager:region:account:secret:epr-db-url-AbCdEf"
   }
   ```

2. **Enable ECS Exec for debugging:**
   ```bash
   export ECS_ENABLE_EXECUTE_COMMAND="true"
   ```

3. **Restrict security group rules:**
   - API: Allow inbound 8080 only from load balancer
   - Outbound: PostgreSQL (5432), Redis (6379), SQS/SNS (443)

4. **Use least-privilege IAM policies:**
   - Execution role: ECR pull, CloudWatch write
   - Task role: SQS read/delete, SNS publish, Secrets Manager read

## Performance Tuning

### Scale API Horizontally

```bash
aws ecs update-service \
  --cluster omen-production \
  --service omen-epr-service \
  --desired-count 3
```

### Increase Worker Throughput

```bash
export EPR_AUDIT_SQS_MAX_MESSAGES="10"
export EPR_AUDIT_SQS_WAIT_TIME="20"
```

### Enable Auto-Scaling

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/omen-production/omen-epr-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10
```

## Support

For issues or questions:
- Check CloudWatch Logs: `/ecs/omen-epr`
- Review ECS Events in console
- Verify environment variable configuration
- Contact platform team

