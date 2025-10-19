"""Remove status column from audit_logs."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_remove_audit_status"
down_revision: Union[str, None] = "0004_add_documents_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("audit_logs", "status")


def downgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
    )
