-- ============================================
-- Entity Permissions Core - Database Schema (SQLite)
-- ============================================
-- This script creates all tables, indexes, and constraints
-- for SQLite databases (used in development).
--
-- Note: SQLite doesn't support:
--   - ENUM types (using CHECK constraints instead)
--   - JSONB (using JSON instead)
--   - UUID type (using CHAR(36) instead)
--   - Triggers for updated_at (handled by application)
--
-- Usage:
--   sqlite3 your_database.db < database_schema_sqlite.sql
--
-- ============================================

-- ============================================
-- TABLES
-- ============================================

-- Entities Table
CREATE TABLE entities (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('issuer', 'spv', 'offering', 'investor', 'agent', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    parent_id CHAR(36) REFERENCES entities(id) ON DELETE SET NULL,
    attributes JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_entities_name_type UNIQUE (name, type)
);

-- Roles Table
CREATE TABLE roles (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(512),
    is_system BOOLEAN NOT NULL DEFAULT 0,
    scope_types JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_roles_name UNIQUE (name)
);

-- Permissions Table
CREATE TABLE permissions (
    id CHAR(36) PRIMARY KEY,
    action VARCHAR(255) NOT NULL,
    description VARCHAR(1024),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_permissions_action UNIQUE (action)
);

-- Role Permissions (Many-to-Many Join Table)
CREATE TABLE role_permissions (
    role_id CHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id CHAR(36) NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

-- Role Assignments Table
CREATE TABLE role_assignments (
    id CHAR(36) PRIMARY KEY,
    principal_id CHAR(36) NOT NULL,
    principal_type VARCHAR(64) NOT NULL DEFAULT 'user',
    entity_id CHAR(36) REFERENCES entities(id) ON DELETE CASCADE,
    role_id CHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    effective_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_assignments_principal_role_entity UNIQUE (principal_id, principal_type, role_id, entity_id)
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    id CHAR(36) PRIMARY KEY,
    sequence INTEGER NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    hash_version INTEGER NOT NULL DEFAULT 1,
    event_id VARCHAR(128),
    source VARCHAR(128) NOT NULL DEFAULT 'entity_permissions_core',
    occurred_at TIMESTAMP NOT NULL,
    actor_id CHAR(36),
    actor_type VARCHAR(64) NOT NULL DEFAULT 'user',
    entity_id CHAR(36),
    entity_type VARCHAR(64),
    action VARCHAR(120) NOT NULL,
    correlation_id VARCHAR(120),
    details JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_audit_logs_event_id UNIQUE (event_id),
    CONSTRAINT uq_audit_logs_sequence UNIQUE (sequence),
    CONSTRAINT ck_audit_logs_previous_hash_length CHECK (length(previous_hash) = 64),
    CONSTRAINT ck_audit_logs_entry_hash_length CHECK (length(entry_hash) = 64)
);

-- Platform Events Table
CREATE TABLE platform_events (
    id CHAR(36) PRIMARY KEY,
    event_id VARCHAR(128) NOT NULL UNIQUE,
    event_type VARCHAR(128) NOT NULL,
    source VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMP NOT NULL,
    correlation_id VARCHAR(128),
    schema_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    payload JSON NOT NULL DEFAULT '{}',
    context JSON NOT NULL DEFAULT '{}',
    delivery_state VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (delivery_state IN ('pending', 'succeeded', 'failed')),
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    last_error VARCHAR(1024),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES
-- ============================================

-- Entities Indexes
CREATE INDEX ix_entities_type ON entities(type);
CREATE INDEX ix_entities_parent ON entities(parent_id);

-- Permissions Indexes
CREATE INDEX ix_permissions_action ON permissions(action);

-- Role Assignments Indexes
CREATE INDEX ix_role_assignments_principal ON role_assignments(principal_id);
CREATE INDEX ix_role_assignments_entity ON role_assignments(entity_id);
CREATE INDEX ix_role_assignments_role ON role_assignments(role_id);

-- Audit Logs Indexes
CREATE INDEX ix_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX ix_audit_logs_entity ON audit_logs(entity_id);
CREATE INDEX ix_audit_logs_action ON audit_logs(action);

-- Platform Events Indexes
CREATE INDEX ix_platform_events_event_type ON platform_events(event_type);
CREATE INDEX ix_platform_events_occurred_at ON platform_events(occurred_at);

-- ============================================
-- END OF SCHEMA
-- ============================================

