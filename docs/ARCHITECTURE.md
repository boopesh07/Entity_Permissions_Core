# Omen Entity & Permissions Core (EPR)

## Context
The Entity & Permissions Core (EPR) powers authorization decisions for the Omen document vault, compliance workflows, and future services. It centralizes the modeling of business entities (issuers, SPVs, offerings, investors, agents), role-based permissions, and policy evaluation. The system must be auditable, secure by default, and extensible for additional entity relationships and authorization semantics.

## Goals
- Provide a stateless REST API for synchronous authorization lookups (`POST /api/v1/authorize`).
- Manage canonical data for entities, roles, role permissions, and assignments between principals and entities.
- Support hierarchical entities with inherited permissions.
- Emit structured audit logs for every mutating event.
- Deploy as a containerized service (ECS) with external PostgreSQL or compatible SQL database.

## Architecture Overview
```
┌───────────────────────┐
│  Frontends / Services │
└──────────┬────────────┘
           │ REST/JSON
┌──────────▼───────────┐
│      FastAPI API     │
├──────────┬───────────┤
│  Service / Use Cases │
├──────────┼───────────┤
│ AuthZ Engine │ Repos │
├──────────┴───────────┤
│   SQLAlchemy ORM +   │
│ Postgres (prod) /    │
│ SQLite (tests/dev)   │
└──────────────────────┘
```

### Components
- **API Layer (FastAPI)**: Request validation (Pydantic), routing, and error handling. API surface includes entity CRUD, role management, assignment management, and authorization checks.
- **Service Layer**: Implements business logic — entity lifecycle, consistent role/permission updates, and evaluation of authorization requests. Exposes transaction-safe use cases.
- **AuthZ Engine**: Resolves permissions by evaluating role assignments, inherited entity relationships, and resource-context rules.
- **Persistence Layer**: SQLAlchemy ORM models with schema changes managed manually (e.g., via Supabase) during the prototype phase. SQLite for local/dev tests, PostgreSQL in production.
- **Settings & DI**: Pydantic `BaseSettings` loads configuration from environment variables (database URL, logging level, etc.). Dependency injection wires sessions and services.
- **Logging & Audit**: Python `logging` with JSON formatting for machine readability. Hooks write audit trails to the database and to stdout for shipping to CloudWatch.

## Key Data Models
- `Entity`: Represents issuers, SPVs, offerings, investors, agents, etc. Supports hierarchical relationships (`parent_id`) and metadata JSON.
- `Role`: Named collection of permissions scoped by entity type.
- `Permission`: Atomic action strings (e.g., `document:upload`). Many-to-many with roles.
- `RoleAssignment`: Links a principal (`user_id`, `principal_type`) to an entity + role pair with effective/expiry timestamps.
- `AuditLog`: Immutable events for create/update/delete actions and authorization evaluations.

## Authorization Evaluation
1. Resolve the target entity (resource).
2. Gather all applicable role assignments for the requesting principal:
   - Direct assignments to the entity.
   - Assignments to ancestor entities (inheritance).
   - Global assignments (entity-less administrative roles).
3. Expand roles into distinct permission strings.
4. Apply optional conditional checks (expiry, principal type, entity type scoping).
5. Return authorized/unauthorized decision.
6. Emit audit record with correlation identifiers.

## Deployment Notes
- Containerized via Docker, packaged with `uvicorn` ASGI server.
- AWS ECS task definition runs one container per task family with environment-injected secrets (`DATABASE_URL`, `LOG_LEVEL`, etc.).
- Build pipeline uses `build.sh` (docker build/test) and `deploy.sh` (push to ECR, update ECS service).
- Observability via structured logs to stdout and health checks via `/healthz`.

## Roadmap
- Integrate with centralized IAM/identity provider for user metadata.
- Extend permissions with ABAC (attribute-based access control) predicates.
- Publish authorization and administration events to EventBridge/SQS.
- Implement hash-chained audit log storage for tamper evidence.
