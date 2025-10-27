# Omen Entity & Permissions Core (EPR)

The Entity & Permissions Core provides canonical models for issuers, SPVs, offerings, investors, and scoped permissions that gate document vault operations. It exposes REST APIs for entity lifecycle management, role and permission administration, and a stateless authorization check consumed by downstream services.

## Features

- FastAPI-based REST service with stateless authorization endpoint (`POST /api/v1/authorize`).
- SQLAlchemy models for entities, roles, permissions, role assignments, and audit logs.
- Append-only, hash-chained audit ledger with tamper detection and replay verification.
- Hierarchical permission inheritance across parent/child entities.
- Structured JSON logging suitable for CloudWatch ingestion.
- Authorization caching backed by Upstash Redis with per-principal invalidation.
- SNS notifications to the document vault service when entities are archived.
- Alembic migrations and ECS-ready Docker packaging.

## Local Development

1. **Install dependencies (Python 3.12)**
   ```bash
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Configure environment variables**
  - Copy `.env` or export the variables manually.  
  - Set `EPR_DATABASE_URL` to your target database (defaults to a local SQLite file).
  - Provide `EPR_REDIS_URL`/`EPR_REDIS_TOKEN` if you want to exercise the shared authorization cache locally (falls back to in-memory when omitted).

3. **Run database migrations**
   ```bash
   EPR_DATABASE_URL="postgresql://..." .venv/bin/alembic upgrade head
   ```

4. **Start the API**
   ```bash
   EPR_DATABASE_URL="postgresql://..." .venv/bin/uvicorn app.main:app --reload --port 8000
   ```

5. **Verify the service**
   ```bash
   curl -sSf http://localhost:8000/healthz
   ```

6. **Run the tests**
   ```bash
   .venv/bin/pytest -vv
   ```

### Quick local smoke test

```bash
# Create an entity
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -d '{"name":"Local Issuer","type":"issuer","status":"active","attributes":{"region":"US"}}'

# Archive the entity (replace <ENTITY_ID>)
curl -X POST http://localhost:8000/api/v1/entities/<ENTITY_ID>/archive
```

You should see the following logs:

- `audit_event` entries for `entity.create` and `entity.archive`
- `entity_created` / `entity_archived` info logs
- `document_vault_event_published` when `EPR_DOCUMENT_VAULT_TOPIC_ARN` is set (or `document_vault_event_skipped` if left empty)

### Authorization Model Highlights

- **Entity uniqueness** – entity names are unique per `type`; duplicate POSTs return HTTP 409.
- **Role uniqueness** – role names are globally unique; creating a role with an existing name also returns HTTP 409.
- **Scope types** – a role’s `scope_types` list limits which entity types it can govern. An empty list means “no restriction”, useful for platform-wide admin roles.
- **Global assignments** – omit `entity_id` (or send `null`) when calling `/api/v1/assignments` to grant a role across all entities.
- **Principal types** – `principal_type` is a descriptive label (e.g., `user`, `service`, `group`) stored for audit context; the service does not currently enforce a closed list.
- **Entity types** – valid values are `issuer`, `spv`, `offering`, `investor`, `agent`, and `other`.

### Environment Variables

The service is configured via the `AppSettings` class in `app/core/config.py`. Key variables:

- `EPR_ENVIRONMENT` (default: `local`)
- `EPR_DATABASE_URL` (default: `sqlite:///./data/epr.db`)
- `EPR_LOG_LEVEL` (default: `INFO`)
- `EPR_LOG_JSON` (default: `true`)
- `EPR_REDIS_URL` (Upstash REST endpoint, required in production)
- `EPR_REDIS_TOKEN` (Upstash REST token, required in production)
- `EPR_REDIS_CACHE_PREFIX` (default: `epr`)
- `EPR_REDIS_CACHE_TTL` (default: `300`, seconds)
- `EPR_DOCUMENT_VAULT_TOPIC_ARN` (SNS topic for entity deletion events)
- `EPR_DOCUMENT_EVENT_SOURCE` (default: `entity_permissions_core`)
- `EPR_AUDIT_SQS_URL` (only required for the background consumer)
- `EPR_AUDIT_SQS_MAX_MESSAGES`, `EPR_AUDIT_SQS_WAIT_TIME`, `EPR_AUDIT_SQS_VISIBILITY_TIMEOUT` (optional tunables)

## REST API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness probe |
| `/api/v1/entities` | POST/GET | Create or list entities |
| `/api/v1/entities/{id}` | GET/PATCH | Retrieve or update an entity |
| `/api/v1/entities/{id}/archive` | POST | Soft-archive an entity |
| `/api/v1/roles` | POST/GET/PATCH | Manage roles and permissions |
| `/api/v1/assignments` | POST/GET | Assign roles to principals |
| `/api/v1/assignments/{id}` | DELETE | Revoke a role assignment |
| `/api/v1/authorize` | POST | Stateless authorization check |

Duplicate entity or role POSTs return `409 Conflict` with a descriptive message. Use the list endpoints to discover existing resources before creating new ones.

All mutating endpoints accept an optional `X-Actor-Id` header to attribute audit log entries.

## Audit producers

Publish audit events to the shared **SNS topic** `arn:aws:sns:us-east-1:116981763412:epr-audit-events`. The service already subscribes the queue `https://sqs.us-east-1.amazonaws.com/116981763412/epr-audit-events-queue` and the audit worker drains it continuously.

### Payload contract

```json
{
  "event_id": "6f4e1a2c-cc1b-4f79-b803-b0f7d8b7f02a",
  "source": "issuer-service",
  "action": "issuer.created",
  "actor_id": "b5db2c29-6f2d-4dc6-9b6b-7827806bd0be",
  "actor_type": "user",
  "entity_id": "0f0f7e13-7cb5-449b-9349-0ed8cc5d9b32",
  "entity_type": "issuer",
  "correlation_id": "req-12345",
  "details": {"issuer_code": "ACME"},
  "occurred_at": "2024-04-14T18:03:11.221208Z"
}
```

- `event_id` – idempotency key (UUID recommended).
- `source` – the producing service (e.g., `issuer-service`).
- `details` – optional JSON metadata.
- `occurred_at` – UTC timestamp; offsets are normalised but must be valid ISO-8601.

### Running the worker locally

```bash
EPR_AUDIT_SQS_URL="https://sqs.<region>.amazonaws.com/<acct>/<queue>" \
AWS_REGION="<region>" \
python -m app.workers.audit_consumer
```

The worker long-polls SQS, validates each message against the `AuditEvent` schema, writes it through `AuditService`, and deletes the message on success. Messages that raise exceptions remain in-flight so SQS retry and DLQ policies apply.

## Document-vault consumer

Entity archives emit `entity.deleted` events to the `EPR_DOCUMENT_VAULT_TOPIC_ARN` topic (production ARN: `arn:aws:sns:us-east-1:116981763412:epr-document-events`). Subscribe your downstream queue/Lambda/HTTP endpoint to that topic. Sample payload:

```json
{
  "event_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "source": "entity_permissions_core",
  "action": "entity.deleted",
  "entity_id": "<ENTITY_UUID>",
  "entity_type": "issuer"
}
```

Use the `entity_id`/`entity_type` pair to cascade document archival or deletion, then acknowledge the message (e.g., delete it from SQS).

---

## Deployment Review & Self-Check (2025-10)

- **ALB integration confirmed** – The ECS service now fronts the API through the public ALB `epr-alb`. Listener `:80` forwards to target group `epr-tg` on container port `8080`. Security groups are locked down so only the ALB SG (`sg-016730c5005c5c7b1`) can reach the task SG (`sg-09b1c41ac8c1d448d`) on `8080`.
- **Health checks verified** – `/healthz` responds with 200 once migrations complete. We tailed `/ecs/omen-epr` logs to confirm startup and applied a health-check grace period as needed during troubleshooting.
- **Operational smoke test** – `curl http://epr-alb-509503971.us-east-1.elb.amazonaws.com/healthz` returns `{"status":"ok"}`, demonstrating end-to-end connectivity through the load balancer.
- **Action items** – Keep `.env` values (`ECS_SUBNET_IDS`, `ECS_SECURITY_GROUP_IDS`) aligned with the active service configuration before running helper scripts; update the health-check grace period if future migrations extend startup time.

No code changes were required for this validation pass; the work consisted of infrastructure wiring, log inspection, and operational verification.

## Audit verification

Use the verification script to recompute the hash chain and detect tampering or reordering:

```bash
python scripts/verify_audit_chain.py --verbose
# or
python -m scripts.verify_audit_chain --verbose
```

You can limit verification to a window with `--start-sequence` and `--end-sequence`. The command exits with status code `1` if the ledger fails validation, making it suitable for cron jobs or EventBridge scheduled tasks.

## Deployment

### Multi-Container Architecture

The deployment uses a **single ECS task** with two containers:
- **API Container** (essential): FastAPI web service on port 8080
- **Audit Worker Container** (non-essential): SQS consumer for external audit events

Both containers share the same Docker image but have different entry points.

### Build the container

```bash
./scripts/build.sh
```

The script runs the test suite (unless `SKIP_TESTS=true`), builds a linux/amd64 image, and pushes it to Amazon ECR.

### Push a release to ECS

Ensure the following environment variables are available before deploying:

**Required:**
- `AWS_REGION`, `AWS_ACCOUNT_ID`
- `ECR_REPOSITORY`
- `ECS_CLUSTER`, `ECS_SERVICE`
- `EXECUTION_ROLE_ARN`, `TASK_ROLE_ARN`
- `ECS_SUBNET_IDS` (comma-separated) and `ECS_SECURITY_GROUP_IDS`
- `EPR_DATABASE_URL`, `EPR_REDIS_URL`, `EPR_REDIS_TOKEN`
- `EPR_DOCUMENT_VAULT_TOPIC_ARN`
- `EPR_AUDIT_SQS_URL` (SQS queue URL for audit worker)

**Optional (with defaults):**
- `EPR_AUDIT_SQS_MAX_MESSAGES` (default: 5)
- `EPR_AUDIT_SQS_WAIT_TIME` (default: 20)
- `EPR_AUDIT_SQS_VISIBILITY_TIMEOUT` (default: 60)
- See `docs/DEPLOYMENT.md` for full list

Then run:

```bash
./scripts/deploy.sh
```

The script builds/pushes the image (unless `SKIP_BUILD=true`), renders `infra/ecs-task-def.json.template`, registers a new task definition, and updates or creates the ECS service. On startup, each task executes `alembic upgrade head` before launching Uvicorn.

**📖 See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for comprehensive deployment guide, troubleshooting, and monitoring instructions.**

### Post-deploy smoke test

Behind a load balancer or API Gateway, hit the health endpoint:

```bash
curl -sSf https://<your-api-endpoint>/healthz
```

For direct testing against a task ENI (public subnet only), ensure the security group allows inbound TCP/8080 before issuing the same curl.

### Schema changes

1. Modify the SQLAlchemy models.
2. Generate a migration: `alembic revision --autogenerate -m "describe change"`.
3. Review the migration file and apply it locally: `alembic upgrade head`.
4. Commit the code + migration and deploy. The production tasks will run `alembic upgrade head` automatically during startup.

## Development Notes

- Alembic migration templates live in `alembic/versions`.
- Structured logging is configured in `app/core/logging.py`.
- Tests use in-memory SQLite with pooled connections.

## Future Enhancements

- Integrate with external identity provider for user metadata enrichment.
- Publish authorization events to EventBridge for downstream workflows.
- Extend the permissions model with attribute-based conditions.
