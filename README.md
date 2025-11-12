# Omen Entity & Permissions Core (EPR)

The Entity & Permissions Core provides canonical models for issuers, SPVs, offerings, investors, and scoped permissions that gate document vault operations. It exposes REST APIs for entity lifecycle management, role and permission administration, and a stateless authorization check consumed by downstream services.

## Features

- FastAPI-based REST service with stateless authorization endpoint (`POST /api/v1/authorize`).
- SQLAlchemy models for entities, roles, permissions, role assignments, and audit logs.
- Events engine that normalizes, persists, and publishes outbound domain events.
- Append-only, hash-chained audit ledger with tamper detection and replay verification.
- Hierarchical permission inheritance across parent/child entities.
- Structured JSON logging suitable for CloudWatch ingestion.
- Authorization caching backed by Upstash Redis with per-principal invalidation.
- SNS notifications to the document vault service when entities are archived.
- ECS-ready Docker packaging.

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

3. **Start the API**
   ```bash
   EPR_DATABASE_URL="postgresql://..." .venv/bin/uvicorn app.main:app --reload --port 8000
   ```

4. **Verify the service**
   ```bash
   curl -sSf http://localhost:8000/healthz
   ```

5. **Run the tests**
   ```bash
   .venv/bin/pytest -vv
   ```

> **Schema changes**: Database schema updates are managed manually (e.g., directly in Supabase). Make sure any manual DDL updates are reflected in the SQLAlchemy models before running the application.

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
- `events_engine_published` when `EPR_DOCUMENT_VAULT_TOPIC_ARN` is set (or `events_engine_publish_skipped` if left empty)

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
- `EPR_DOCUMENT_VAULT_TOPIC_ARN` (SNS topic for outbound domain events; optional locally)
- `EPR_DOCUMENT_EVENT_SOURCE` (default: `entity_permissions_core`)
- `EPR_AUDIT_SQS_URL` (only required for the background consumer)
- `EPR_AUDIT_SQS_MAX_MESSAGES`, `EPR_AUDIT_SQS_WAIT_TIME`, `EPR_AUDIT_SQS_VISIBILITY_TIMEOUT` (optional tunables)
- `EPR_EVENT_PUBLISH_ATTEMPTS` (default: `2`)
- `EPR_TEMPORAL_HOST`, `EPR_TEMPORAL_NAMESPACE`, `EPR_TEMPORAL_API_KEY` (required to enable Temporal workflows)
- `EPR_TEMPORAL_TASK_QUEUE` (default: `omen-workflows`)
- `EPR_TEMPORAL_TLS_ENABLED` (default: `true`)

## Event & Workflow Engine (EWE)

The Events Engine (`app/events_engine`) centralizes outbound event emission and inbound ingestion. The companion Workflow Engine (`app/workflow_engine`) is scaffolded for Temporal-based automation.

### Responsibilities

- Normalize outbound events into a canonical envelope and persist them.
- Publish events to SNS (using `EPR_DOCUMENT_VAULT_TOPIC_ARN`) with consistent attributes.
- Maintain the `platform_events` table for deterministic replay and auditability.
- Expose `/api/v1/events` so upstream systems (Document Vault, onboarding flows, etc.) can ingest events directly with idempotency guarantees.
- Consume audit events from SQS via `AuditSQSEventConsumer`, feeding `AuditService`.
- Trigger Temporal workflows for entity, document, and permission lifecycle automations.

### Key Workflows

- **Entity Cascade Archive** – triggered by `entity.archived` when an entity is soft-archived. Downstream services subscribe to this event to revoke permissions, archive documents, or launch workflows.
- **Audit Ingestion** – SNS → SQS audit events are drained by the new consumer module and appended to the hash-chained `audit_logs` table.
- **Permission Change Automations (planned)** – workflow stubs exist to coordinate cache invalidation or long-running tasks once Temporal integration lands.

### Architecture Overview

```
EntityService.archive ──► EventDispatcher.publish_event ──► SNS Topic (EPR_DOCUMENT_VAULT_TOPIC_ARN)
                                  │
                                  └─► platform_events table (immutable ledger)

SNS (EPR audit topic) ─► SQS (EPR_AUDIT_SQS_URL) ─► AuditSQSEventConsumer ─► AuditService.record_event
```

### Data Model

- **platform_events** – immutable ledger storing envelope fields (`event_id`, `event_type`, `source`, `occurred_at`, `payload`, `context`, etc.) plus indexes on `event_type` and `occurred_at`.
- **Audit tables** – unchanged; still enforce the hash chain for inbound audit events.

If you manage schema manually, apply the following SQL (PostgreSQL):

```sql
CREATE TABLE platform_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(128) UNIQUE NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    source VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    correlation_id VARCHAR(128),
    schema_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    delivery_state VARCHAR(16) NOT NULL DEFAULT 'pending',
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    last_error VARCHAR(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_platform_events_event_type ON platform_events (event_type);
CREATE INDEX ix_platform_events_occurred_at ON platform_events (occurred_at);

ALTER TABLE platform_events
    ADD CONSTRAINT ck_platform_events_delivery_state
        CHECK (delivery_state IN ('pending', 'succeeded', 'failed'));
```

### Event Ingestion API

The Event Engine now exposes `/api/v1/events`:

- **POST `/api/v1/events`** – ingest an event. The service generates `event_id`, persists the record, publishes it to SNS with an outbox retry loop (2 attempts), and returns the delivery state. Provide `correlation_id` for idempotency.
- **GET `/api/v1/events`** – paginate/filter by `event_type` or `source` to inspect recent events.
- **GET `/api/v1/events/{event_id}`** – retrieve a specific event and its delivery metadata.

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{
        "event_type": "document.verified",
        "source": "document_vault",
        "payload": {"document_id": "abc-123"},
        "context": {"actor_id": "user-42"},
        "correlation_id": "doc-abc-123"
      }'
```

#### How other services should publish events

1. **Identify the event** – choose a descriptive `event_type` (`document.verified`, `permission.revoked`, etc.) and a stable `source` (e.g., `document_vault`).  
2. **Build the payload** – include only JSON-safe data needed by downstream consumers. Large blobs or PII should live elsewhere.  
3. **Provide `correlation_id`** – use a deterministic identifier (document ID, job ID) so retries return the original event instead of duplicating it.  
4. **POST to `/api/v1/events`** – include the payload above; the Event Engine will generate `event_id`, persist the ledger entry, publish to SNS, and trigger any mapped workflows.  
5. **Handle responses** – a `201` response includes `delivery_state`. If it is `failed`, log the `last_error` and retry later.  
6. **Security** – ensure the calling service authenticates the request the same way it accesses other EPR APIs (e.g., private networking, API gateway tokens, etc.).

Example (Document Vault):

```bash
curl -X POST https://epr.api.internal/api/v1/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SERVICE_TOKEN>" \
  -d '{
        "event_type": "document.verified",
        "source": "document_vault",
        "payload": {
          "document_id": "doc_123",
          "issuer_id": "issuer_456",
          "verified_by": "user_999"
        },
        "context": {"actor_id": "user_999"},
        "correlation_id": "document_vault:doc_123:verification"
      }'
```

Any future microservice can follow the same pattern: define the event, include a correlation identifier, and call `/api/v1/events`. The Event Engine handles persistence, SNS fan-out, and workflow orchestration.

### Module Tour

- `app/events_engine/service.py` – ingestion, dedupe, and query helpers backing the REST API.
- `app/events_engine/dispatcher.py` – persists events and publishes them with built-in retry/outbox state.
- `app/events_engine/publisher.py` – transport abstraction (`SnsEventPublisher` / `NullEventPublisher`).
- `app/events_engine/consumers/base.py` – reusable SQS polling with SNS envelope handling.
- `app/events_engine/consumers/audit.py` – audit ingestion wired through the dispatcher.
- `app/workflow_orchestration/` – Temporal workflows, activities, and orchestration helpers.

### Workflow Orchestration

Configure `EPR_TEMPORAL_HOST`, `EPR_TEMPORAL_NAMESPACE`, `EPR_TEMPORAL_API_KEY`, and optional `EPR_TEMPORAL_TASK_QUEUE`, then start the worker locally:

```bash
python -m app.workflow_orchestration.worker
```

The orchestrator automatically reacts to:

| Event Type | Workflow |
|------------|----------|
| `entity.archived` | `EntityCascadeArchiveWorkflow` – archives vault documents & invalidates permissions. |
| `document.verified` | `DocumentVerifiedWorkflow` – simulates receipt issuance. |
| `role.assignment.changed`, `role.updated` | `PermissionChangeWorkflow` – clears authorization caches. |

If Temporal is not configured, workflow dispatch is skipped but events are still persisted and published.

#### Module layout

| Path | Responsibility |
|------|----------------|
| `app/workflow_orchestration/config.py` | Loads Temporal host/namespace/API key/task queue settings (`EPR_TEMPORAL_*`). |
| `app/workflow_orchestration/client.py` | Creates authenticated Temporal clients (TLS on by default). |
| `app/workflow_orchestration/activities.py` | Side-effecting activities (document archival, cache invalidation, receipt issuance). Extend these to integrate with real downstream services. |
| `app/workflow_orchestration/workflows/` | Deterministic workflow definitions orchestrating the activities. |
| `app/workflow_orchestration/orchestrator.py` | Maps platform events to workflow classes and starts them with deterministic IDs (`<WorkflowName>-<event_id>`). |
| `app/workflow_orchestration/worker.py` | Boots a Temporal worker that registers all workflows/activities against the configured task queue. |

#### Running the worker in other environments

1. Export the Temporal credentials (see **Environment Variables** above).  
2. Use the same container image as the API, but override the command to `python -m app.workflow_orchestration.worker`.  
3. Ensure outbound network access to `EPR_TEMPORAL_HOST` (`us-east-1.aws.api.temporal.io:7233` in production) and that the API key has workflow create permissions.  
4. Monitor worker logs for `workflow_started`, `workflow_issue_receipt`, etc. Failures are surfaced as `workflow_start_failed` or activity logs; Temporal will also surface them in its UI.

#### Observability & replay

- Every ingested event is written to `platform_events` with `delivery_state` (`pending`, `succeeded`, `failed`) and `delivery_attempts`. Failed publishes bubble up to the caller and remain flagged for manual replay.  
- Workflow launches log `workflow_started`; if Temporal is disabled in an environment, the orchestrator logs `workflow_skipped_temporal_disabled` but the REST API still returns `201`.  
- Use `/api/v1/events/{event_id}` to inspect the payload passed into a workflow or to derive a deterministic workflow ID for replaying via the Temporal CLI/UI.  
- To manually replay, re-POST the event with the same `correlation_id` (ingestion will return the existing row) and use the persisted payload to start a workflow run via Temporal tooling.

### Testing

- Engine coverage lives in `tests/events_engine/` (dispatcher, integration with EntityService, consumer utilities, audit handler).
- Workflow scaffolding is verified in `tests/workflow_engine/`.
- Existing API/domain tests reuse a dispatcher stub defined in `tests/conftest.py`.

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
| `/api/v1/events` | POST/GET | Ingest or list platform events |
| `/api/v1/events/{event_id}` | GET | Fetch a specific event |

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

## Event consumers

Entity archives emit `entity.archived` events to the `EPR_DOCUMENT_VAULT_TOPIC_ARN` topic (production ARN: `arn:aws:sns:us-east-1:116981763412:epr-document-events`). Subscribe your downstream queue/Lambda/HTTP endpoint to that topic. Sample payload:

```json
{
  "event_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "event_type": "entity.archived",
  "source": "entity_permissions_core",
  "occurred_at": "2025-10-30T21:11:00Z",
  "payload": {
    "entity_id": "<ENTITY_UUID>",
    "entity_type": "issuer"
  },
  "context": {}
}
```

Use the payload to cascade document archival, invalidate caches, or trigger workflows. Remove messages from your queue (e.g., SQS `DeleteMessage`) after successful processing.

---

## Deployment Review & Self-Check (2025-10)

- **ALB integration confirmed** – The ECS service now fronts the API through the public ALB `epr-alb`. Listener `:80` forwards to target group `epr-tg` on container port `8080`. Security groups are locked down so only the ALB SG (`sg-016730c5005c5c7b1`) can reach the task SG (`sg-09b1c41ac8c1d448d`) on `8080`.
- **Health checks verified** – `/healthz` responds with 200 once the API finishes booting. We tailed `/ecs/omen-epr` logs to confirm startup and applied a health-check grace period as needed during troubleshooting.
- **Operational smoke test** – `curl http://epr-alb-509503971.us-east-1.elb.amazonaws.com/healthz` returns `{"status":"ok"}`, demonstrating end-to-end connectivity through the load balancer.
- **Action items** – Keep `.env` values (`ECS_SUBNET_IDS`, `ECS_SECURITY_GROUP_IDS`) aligned with the active service configuration before running helper scripts; update the health-check grace period if startup time changes.

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

The script builds/pushes the image (unless `SKIP_BUILD=true`), renders `infra/ecs-task-def.json.template`, registers a new task definition, and updates or creates the ECS service. On startup, each task now launches Uvicorn directly—ensure your database schema updates have already been applied manually (e.g., via Supabase) before deploying.

**📖 See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for comprehensive deployment guide, troubleshooting, and monitoring instructions.**

### Post-deploy smoke test

Behind a load balancer or API Gateway, hit the health endpoint:

```bash
curl -sSf https://<your-api-endpoint>/healthz
```

For direct testing against a task ENI (public subnet only), ensure the security group allows inbound TCP/8080 before issuing the same curl.

### Schema changes

During the prototype phase all database schema changes are performed manually:

1. Update the SQLAlchemy models to reflect the desired columns/constraints.
2. Apply the equivalent DDL directly in Supabase (or your chosen database console).
3. Deploy the service once the target environment has the updated schema.

Because migrations are not automated, double-check that each environment’s schema matches the models before shipping new features.

## Development Notes

- Structured logging is configured in `app/core/logging.py`.
- Tests use in-memory SQLite with pooled connections.

## Future Enhancements

- Integrate with external identity provider for user metadata enrichment.
- Publish authorization events to EventBridge for downstream workflows.
- Extend the permissions model with attribute-based conditions.
