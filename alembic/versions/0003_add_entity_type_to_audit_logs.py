"""Add entity_type to audit_logs."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_audit_entity_type"
down_revision: Union[str, None] = "0002_entity_name_type_uc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("entity_type", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "entity_type")
