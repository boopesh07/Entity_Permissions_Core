"""Initial schema for entities, roles, and permissions."""

from __future__ import annotations
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from app.models.types import GUID, JSONType

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Initial schema for entities, roles, and permissions."""
    entity_type_ref = sa.Enum(
        "issuer",
        "spv",
        "offering",
        "investor",
        "agent",
        "other",
        name="entity_type",
        native_enum=False,
    )
    entity_status_ref = sa.Enum(
        "active",
        "inactive",
        "archived",
        name="entity_status",
        native_enum=False,
    )

    op.create_table(
        "entities",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", entity_type_ref, nullable=False),
        sa.Column("status", entity_status_ref, nullable=False),
        sa.Column("parent_id", GUID(), nullable=True),
        sa.Column("attributes", JSONType(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["entities.id"], name=op.f("fk_entities_parent_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
    )
    op.create_index(op.f("ix_entities_parent"), "entities", ["parent_id"], unique=False)
    op.create_index(op.f("ix_entities_type"), "entities", ["type"], unique=False)
    op.create_table(
        "roles",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("scope_types", JSONType(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("name", name=op.f("uq_roles_name")),
    )
    op.create_table(
        "permissions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("action", name=op.f("uq_permissions_action")),
    )
    op.create_index(op.f("ix_permissions_action"), "permissions", ["action"], unique=False)
    op.create_table(
        "role_assignments",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("principal_id", GUID(), nullable=False),
        sa.Column("principal_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", GUID(), nullable=True),
        sa.Column("role_id", GUID(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_role_assignments_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name=op.f("fk_role_assignments_role_id_roles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_assignments")),
        sa.UniqueConstraint("principal_id", "principal_type", "role_id", "entity_id", name=op.f("uq_role_assignments_principal_id_principal_type_role_id_entity_id")),
    )
    op.create_index(op.f("ix_role_assignments_entity"), "role_assignments", ["entity_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_principal"), "role_assignments", ["principal_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_role"), "role_assignments", ["role_id"], unique=False)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", GUID(), nullable=False),
        sa.Column("permission_id", GUID(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], name=op.f("fk_role_permissions_permission_id_permissions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name=op.f("fk_role_permissions_role_id_roles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_role_permissions")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("actor_id", GUID(), nullable=True),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", GUID(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("details", JSONType(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity"), "audit_logs", ["entity_id"], unique=False)


def downgrade() -> None:
    """Drops all tables and custom types."""
    op.drop_index(op.f("ix_audit_logs_entity"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_role_assignments_role"), table_name="role_assignments")
    op.drop_index(op.f("ix_role_assignments_principal"), table_name="role_assignments")
    op.drop_index(op.f("ix_role_assignments_entity"), table_name="role_assignments")
    op.drop_table("role_assignments")
    op.drop_index(op.f("ix_permissions_action"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_index(op.f("ix_entities_type"), table_name="entities")
    op.drop_index(op.f("ix_entities_parent"), table_name="entities")
    op.drop_table("entities")
