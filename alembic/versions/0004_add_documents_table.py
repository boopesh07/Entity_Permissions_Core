"""Add documents table for document vault integration."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.types import GUID, JSONType


revision: str = "0004_add_documents_table"
down_revision: Union[str, None] = "0003_add_audit_entity_type"
# keep branch_labels / depends_on defaulted to None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    document_entity_type = sa.Enum(
        "issuer",
        "investor",
        "deal",
        "token",
        "compliance",
        name="documententitytype",
        native_enum=False,
    )
    document_type = sa.Enum(
        "operating_agreement",
        "offering_memorandum",
        "subscription",
        "kyc",
        "audit_report",
        "other",
        name="documenttype",
        native_enum=False,
    )
    document_status = sa.Enum(
        "uploaded",
        "verified",
        "mismatch",
        "archived",
        name="documentstatus",
        native_enum=False,
    )

    op.create_table(
        "documents",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("entity_type", document_entity_type, nullable=False),
        sa.Column("entity_id", GUID(), nullable=False),
        sa.Column("token_id", sa.Integer(), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_bucket", sa.String(length=63), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False, unique=True),
        sa.Column("storage_version_id", sa.String(length=255), nullable=True),
        sa.Column("sha256_hash", sa.String(length=128), nullable=False),
        sa.Column("hash_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            document_status,
            nullable=False,
            server_default=sa.text("'uploaded'"),
        ),
        sa.Column("on_chain_reference", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by", GUID(), nullable=False),
        sa.Column("verified_by", GUID(), nullable=True),
        sa.Column("archived_by", GUID(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONType(), nullable=True),
    )
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_sha256_hash", table_name="documents")
    op.drop_table("documents")
