# Omen Entity & Permissions Core (EPR)

The Entity & Permissions Core provides canonical models for issuers, SPVs, offerings, investors, and scoped permissions that gate document vault operations. It exposes REST APIs for entity lifecycle management, role and permission administration, and a stateless authorization check consumed by downstream services.

## Features

- FastAPI-based REST service with stateless authorization endpoint (`POST /api/v1/authorize`).
- SQLAlchemy models for entities, roles, permissions, role assignments, and audit logs.
- Hierarchical permission inheritance across parent/child entities.
- Structured JSON logging suitable for CloudWatch ingestion.
- Alembic migrations and ECS-ready Docker packaging.

## Getting Started

1. **Create a virtual environment (Python 3.12) & install dependencies**
   ```bash
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Run database migrations** (defaults to local SQLite storage at `./data/epr.db`):
   ```bash
   .venv/bin/alembic upgrade head
   ```

3. **Start the API locally**
   ```bash
   .venv/bin/uvicorn app.main:app --reload --port 8000
   ```

4. **Run the test suite**
   ```bash
   .venv/bin/python -m pytest -vv
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

## Docker & Deployment

Build and test an image:

```bash
./scripts/build.sh
```

Run the container locally:

```bash
docker run --rm -p 8080:8080 \
  -e EPR_DATABASE_URL='sqlite:////data/epr.db' \
  omen-epr:latest
```

Trigger migrations and start the app inside the container with `RUN_MIGRATIONS=true` (default).

Deploy to AWS ECS:

```bash
AWS_REGION=us-east-1 \
AWS_ACCOUNT_ID=123456789012 \
ECR_REPOSITORY=omen-epr \
ECS_CLUSTER=omen-core \
ECS_SERVICE=omen-epr-svc \
./scripts/deploy.sh
```

The deployment script pushes the image to ECR and forces a new ECS deployment.

## Development Notes

- Alembic migration templates live in `alembic/versions`.
- Structured logging is configured in `app/core/logging.py`.
- Tests use in-memory SQLite with pooled connections.
- Update `TODO.md` as additional roadmap items are delivered.

## Future Enhancements

- Integrate with external identity provider for user metadata enrichment.
- Publish authorization events to EventBridge for downstream workflows.
- Extend the permissions model with attribute-based conditions.
