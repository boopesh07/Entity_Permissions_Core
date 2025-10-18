# Omen Entity & Permissions Core (EPR)

The Entity & Permissions Core provides canonical models for issuers, SPVs, offerings, investors, and scoped permissions that gate document vault operations. It exposes REST APIs for entity lifecycle management, role and permission administration, and a stateless authorization check consumed by downstream services.

## Features

- FastAPI-based REST service with stateless authorization endpoint (`POST /api/v1/authorize`).
- SQLAlchemy models for entities, roles, permissions, role assignments, and audit logs.
- Hierarchical permission inheritance across parent/child entities.
- Structured JSON logging suitable for CloudWatch ingestion.
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

## Deployment

### Build the container

```bash
./scripts/build.sh
```

The script runs the test suite (unless `SKIP_TESTS=true`), builds a linux/amd64 image, and pushes it to Amazon ECR.

### Push a release to ECS

Ensure the following environment variables are available before deploying:

- `AWS_REGION`, `AWS_ACCOUNT_ID`
- `ECR_REPOSITORY`
- `ECS_CLUSTER`, `ECS_SERVICE`
- `EXECUTION_ROLE_ARN`, `TASK_ROLE_ARN`
- `ECS_SUBNET_IDS` (comma-separated) and `ECS_SECURITY_GROUP_IDS`
- Application settings such as `EPR_DATABASE_URL`

Then run:

```bash
./scripts/deploy.sh
```

The script builds/pushes the image (unless `SKIP_BUILD=true`), renders `infra/ecs-task-def.json.template`, registers a new task definition, and updates or creates the ECS service. On startup, each task executes `alembic upgrade head` before launching Uvicorn.

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
