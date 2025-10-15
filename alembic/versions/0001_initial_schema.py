"""Initial schema for entities, roles, and permissions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    entity_type_enum = sa.Enum(
        "issuer",
        "spv",
        "offering",
        "investor",
        "agent",
        "other",
        name="entity_type",
    )
    entity_status_enum = sa.Enum("active", "inactive", "archived", name="entity_status")

    entity_type_enum.create(op.get_bind(), checkfirst=True)
    entity_status_enum.create(op.get_bind(), checkfirst=True)

    entity_type = sa.Enum(
        "issuer",
        "spv",
        "offering",
        "investor",
        "agent",
        "other",
        name="entity_type",
        create_type=False,
    )
    entity_status = sa.Enum("active", "inactive", "archived", name="entity_status", create_type=False)

    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", entity_type, nullable=False),
        sa.Column("status", entity_status, nullable=False, server_default="active"),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_entities_type", "entities", ["type"])
    op.create_index("ix_entities_parent", "entities", ["parent_id"])

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("action", name="uq_permissions_action"),
    )
    op.create_index("ix_permissions_action", "permissions", ["action"])

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scope_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("actor_type", sa.String(length=64), nullable=False, server_default="user"),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.String(length=36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    op.create_table(
        "role_assignments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("principal_id", sa.String(length=36), nullable=False),
        sa.Column("principal_type", sa.String(length=64), nullable=False, server_default="user"),
        sa.Column("entity_id", sa.String(length=36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Index("ix_role_assignments_principal", "principal_id"),
        sa.Index("ix_role_assignments_entity", "entity_id"),
        sa.Index("ix_role_assignments_role", "role_id"),
        sa.UniqueConstraint(
            "principal_id",
            "principal_type",
            "role_id",
            "entity_id",
            name="uq_role_assignments_principal_role_entity",
        ),
    )


def downgrade() -> None:
    op.drop_table("role_assignments")
    op.drop_table("role_permissions")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("roles")
    op.drop_index("ix_permissions_action", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_entities_parent", table_name="entities")
    op.drop_index("ix_entities_type", table_name="entities")
    op.drop_table("entities")

    entity_type_enum = sa.Enum(
        "issuer",
        "spv",
        "offering",
        "investor",
        "agent",
        "other",
        name="entity_type",
    )
    entity_status_enum = sa.Enum("active", "inactive", "archived", name="entity_status")
    entity_type_enum.drop(op.get_bind(), checkfirst=True)
    entity_status_enum.drop(op.get_bind(), checkfirst=True)
