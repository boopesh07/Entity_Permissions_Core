# Entity & Permissions Core

The Entity & Permissions Core (EPR) is Omen’s authoritative service for modelling business entities, defining reusable roles and permissions, and answering authorization checks used by downstream workloads (Document Vault, onboarding flows, investor portals, etc.). It provides a consistent RBAC foundation that other microservices can rely on without duplicating permission logic.

---

## Quick Start Workflows

### 1) Register a New Entity
1. **Create** the entity with its type (`issuer`, `spv`, `offering`, `investor`, `agent`, or `other`) and optional parent relationship using `POST /api/v1/entities`.
2. The service enforces uniqueness of `name + type`, persists custom JSON attributes, and mirrors the action into the audit log (author attribution via the optional `X-Actor-Id` header).
3. **Retrieve** or **list** entities via `GET /api/v1/entities/{id}` or `GET /api/v1/entities?type=issuer` to confirm the registry contents.

### 2) Define a Role and Its Permissions
1. Baseline permission actions (e.g., `document.read`, `entity.manage`) are created once on startup; add new ones dynamically by including them in role payloads.
2. Call `POST /api/v1/roles` with a unique name, human description, optional `scope_types` restriction (limits which entity types the role can govern), and the list of permission actions.
3. Update descriptions, scopes, or permissions later with `PATCH /api/v1/roles/{role_id}`; all changes are audit-logged for compliance review.

### 3) Assign Roles to Principals
1. Use `POST /api/v1/assignments` to bind a role to a principal (`principal_id` + `principal_type`). Provide `entity_id` for scoped assignments or omit it for global access.
2. The service enforces scope constraints (a role with `scope_types=["issuer"]` cannot be assigned to an `investor` entity) and deduplicates appointments.
3. List or revoke assignments with `GET /api/v1/assignments?principal_id=…` and `DELETE /api/v1/assignments/{assignment_id}` as principals churn.

### 4) Perform Stateless Authorization Checks
1. Downstream services call `POST /api/v1/authorize` with the target `principal_id`, requested `permission`, and the optional `entity_id`.
2. EPR evaluates direct role assignments, inherited permissions from parent entities, effective / expiry windows, and returns `{ "authorized": true | false }`.
3. Consumers cache the boolean result for their own session logic; the core remains stateless and horizontally scalable.

---

## Core Concepts

- **Entity Registry** – Hierarchical catalogue of issuers, SPVs, offerings, investors, agents, etc. Each entity can carry ad-hoc JSON attributes and be soft-archived without destroying history.
- **Roles & Permissions** – Roles aggregate atomic permission actions (strings). `scope_types` limit the entity types a role may govern. System roles (`is_system=true`) are seeded through configuration to guarantee baseline coverage.
- **Role Assignments** – Bind principals (users, services, groups) to roles, optionally scoped to specific entities. Assignments support future-dated `effective_at` and optional `expires_at` to model temporary access.
- **Authorization Engine** – Stateless evaluation that looks up relevant assignments, traverses parent entity hierarchy when necessary, and answers yes/no without persisting session data.
- **Audit Trail** – Every mutating action (entity create, role update, assignment revoke, failed permission checks, etc.) is persisted to `audit_logs` and mirrored to structured JSON logs suitable for CloudWatch ingestion.
- **Startup Safety Nets** – During application lifespan startup the `RoleService.ensure_baseline_permissions` method guarantees that configured permission actions exist before any roles or assignments use them.

---

## Data Model (at a Glance)

- **`entities`** – Core registry (`id`, `name`, `type`, `status`, `parent_id`, `attributes`, timestamps).
- **`roles`** – Reusable roles (`id`, `name`, `description`, `scope_types`, `is_system`, timestamps).
- **`permissions`** – Atomic actions (`id`, `action`, `description`).
- **`role_permissions`** – Join table linking roles ↔ permissions.
- **`role_assignments`** – Principal ↔ role ↔ entity bindings (`principal_id`, `principal_type`, `entity_id`, `role_id`, `effective_at`, `expires_at`).
- **`audit_logs`** – Structured audit events (`actor_id`, `actor_type`, `entity_id`, `action`, `status`, `details`, `correlation_id`).

---

## API Overview

Full OpenAPI docs are exposed at `/docs` when the service is running.

### Entities
- `POST /api/v1/entities` – Create a new entity; rejects duplicates (`409 Conflict`) by `name+type`.
- `GET /api/v1/entities/{id}` – Retrieve entity details.
- `GET /api/v1/entities` – List entities, filterable by `type` (multi-value) and `parent_id`.
- `PATCH /api/v1/entities/{id}` – Update metadata or attributes.
- `POST /api/v1/entities/{id}/archive` – Soft-archive while retaining relationships and audit history.

### Roles & Permissions
- `POST /api/v1/roles` – Create a role and attach permission actions.
- `GET /api/v1/roles` – List all roles (system + custom).
- `PATCH /api/v1/roles/{id}` – Update description, scope, or permission membership.

### Role Assignments
- `POST /api/v1/assignments` – Assign a role to a principal (entity-scoped or global).
- `GET /api/v1/assignments` – Query assignments by `principal_id` and/or `entity_id`.
- `DELETE /api/v1/assignments/{id}` – Revoke an assignment.

### Authorization
- `POST /api/v1/authorize` – Stateless check returning `{ "authorized": bool }` based on principal, permission, and optional entity context. Ideal target for a small TTL cache; invalidated on role or assignment change.

### Support
- `GET /healthz` – Lightweight liveness check for ECS / Kubernetes probes.

All mutating endpoints accept an optional `X-Actor-Id` header to attribute audit entries. Idempotent behaviour (e.g., duplicate assignments) returns the existing record to simplify client retries.

---

## System Interactions & Integrations

- **Document Vault & Other Services** – The vault consults `/authorize` before allowing uploads, downloads, or archival. Other microservices can follow the same pattern to centralize access control.
- **Startup Seed** – During the FastAPI lifespan hook (`app.main.lifespan`) the service ensures configured baseline permissions exist, enabling infrastructure-as-code environments to declare required actions without manual SQL.
- **Observability** – Structured logs include action, actor, entity, and correlation metadata, making it easy to assemble audit traces alongside the relational audit table.
- **Extensibility Hooks** – The role/permission services are constructed with dependency injection (see `app/api/dependencies.py`) to enable future message publishing or caching layers without touching the HTTP handlers.
- **Caching** – For high-volume authorization calls, place a short-lived cache (e.g., Redis) in front of `/authorize`, keyed by `principal_id + permission (+ entity_id)`. Invalidate cached entries after role, permission, or assignment mutations to keep decisions fresh.

---

## Security & Compliance Highlights

- **TLS Everywhere** – Clients connect over HTTPS; database connections enforce `sslmode=require`.
- **Principle of Least Privilege** – Roles can be scoped to specific entity types, and assignments can be entity-specific or globally restricted with expiry windows.
- **Immutable Audit Trail** – Every mutating action produces an `audit_log` entry and a structured log event, providing full traceability for regulators and internal security teams.
- **No Shared Secrets in Payloads** – Credentials (database URL, baseline permissions) are supplied via environment variables and should be sourced from AWS SSM or Secrets Manager in production deployments.
- **Horizontal Scale Friendly** – Stateless `/authorize` endpoint and idempotent role assignment logic enable safe multi-instance deployments behind ECS or Kubernetes without sticky sessions.

---

## Roadmap Ideas

- **External Identity Enrichment** – Join cached identity metadata (names, emails, group memberships) for richer audit logging.
- **Event Publishing** – Emit role/assignment change events to EventBridge or SNS for downstream notification systems.
- **Attribute-Based Access Control (ABAC)** – Extend assignments with contextual rules (e.g., jurisdiction, investment size).
- **Bulk Administration APIs** – Import/export roles and assignments to streamline large tenant onboarding.
- **Continuous Authorization Monitoring** – Scheduled jobs to detect stale assignments, soon-to-expire access, or orphaned entities.

---

*Last updated: 2025-10-15*
