-- ============================================
-- Entity Permissions Core - Database Schema
-- ============================================
-- This script creates all tables, indexes, enums, and constraints
-- for the Entity Permissions Core service.
--
-- Database: PostgreSQL (recommended for production)
-- Compatible: SQLite (for development, with some limitations)
--
-- Usage:
--   psql -U your_user -d your_database -f database_schema.sql
--   OR
--   sqlite3 your_database.db < database_schema.sql
--
-- Note: Requires PostgreSQL 13+ for gen_random_uuid()
--       For older versions, replace with: uuid_generate_v4()
--       (requires: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";)
--
-- ============================================

-- ============================================
-- ENUMS
-- ============================================

-- Entity Type Enum
CREATE TYPE entity_type AS ENUM (
    'issuer',
    'spv',
    'offering',
    'investor',
    'agent',
    'other'
);

-- Entity Status Enum
CREATE TYPE entity_status AS ENUM (
    'active',
    'inactive',
    'archived'
);

-- Platform Event Delivery State Enum
CREATE TYPE platform_event_delivery_state AS ENUM (
    'pending',
    'succeeded',
    'failed'
);

-- ============================================
-- TABLES
-- ============================================

-- Entities Table
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type entity_type NOT NULL,
    status entity_status NOT NULL DEFAULT 'active',
    parent_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    attributes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_entities_name_type UNIQUE (name, type)
);

-- Roles Table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    description VARCHAR(512),
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    scope_types JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_roles_name UNIQUE (name)
);

-- Permissions Table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(255) NOT NULL,
    description VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_permissions_action UNIQUE (action)
);

-- Role Permissions (Many-to-Many Join Table)
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

-- Role Assignments Table
CREATE TABLE role_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id UUID NOT NULL,
    principal_type VARCHAR(64) NOT NULL DEFAULT 'user',
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    effective_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_role_assignments_principal_role_entity UNIQUE (principal_id, principal_type, role_id, entity_id)
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence BIGINT NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    hash_version INTEGER NOT NULL DEFAULT 1,
    event_id VARCHAR(128),
    source VARCHAR(128) NOT NULL DEFAULT 'entity_permissions_core',
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    actor_id UUID,
    actor_type VARCHAR(64) NOT NULL DEFAULT 'user',
    entity_id UUID,
    entity_type VARCHAR(64),
    action VARCHAR(120) NOT NULL,
    correlation_id VARCHAR(120),
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_audit_logs_event_id UNIQUE (event_id),
    CONSTRAINT uq_audit_logs_sequence UNIQUE (sequence),
    CONSTRAINT ck_audit_logs_previous_hash_length CHECK (length(previous_hash) = 64),
    CONSTRAINT ck_audit_logs_entry_hash_length CHECK (length(entry_hash) = 64)
);

-- Platform Events Table
CREATE TABLE platform_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(128) NOT NULL UNIQUE,
    event_type VARCHAR(128) NOT NULL,
    source VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    correlation_id VARCHAR(128),
    schema_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    payload JSONB NOT NULL DEFAULT '{}',
    context JSONB NOT NULL DEFAULT '{}',
    delivery_state platform_event_delivery_state NOT NULL DEFAULT 'pending',
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    last_error VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
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
-- TRIGGERS (for updated_at timestamps)
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at
    BEFORE UPDATE ON permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_role_assignments_updated_at
    BEFORE UPDATE ON role_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audit_logs_updated_at
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_platform_events_updated_at
    BEFORE UPDATE ON platform_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE entities IS 'Core entity model representing issuers, offerings, investors, agents, etc.';
COMMENT ON TABLE roles IS 'Composable roles linking to permissions and assignments';
COMMENT ON TABLE permissions IS 'Atomic permissions identified by action strings';
COMMENT ON TABLE role_permissions IS 'Many-to-many join table between roles and permissions';
COMMENT ON TABLE role_assignments IS 'Assigns roles to principals (users) for entities';
COMMENT ON TABLE audit_logs IS 'Immutable audit log entries for chain verification and traceability';
COMMENT ON TABLE platform_events IS 'Normalized platform events stored by the events engine';

-- ============================================
-- END OF SCHEMA
-- ============================================

