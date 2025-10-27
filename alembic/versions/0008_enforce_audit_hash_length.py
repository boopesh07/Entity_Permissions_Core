"""Enforce audit hash length consistency."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008_enforce_audit_hash_length"
down_revision: Union[str, None] = "0007_add_processed_events_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column(
            "previous_hash",
            existing_type=sa.String(length=128),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "entry_hash",
            existing_type=sa.String(length=128),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_audit_logs_previous_hash_length",
            "length(previous_hash) = 64",
        )
        batch_op.create_check_constraint(
            "ck_audit_logs_entry_hash_length",
            "length(entry_hash) = 64",
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint("ck_audit_logs_entry_hash_length", type_="check")
        batch_op.drop_constraint("ck_audit_logs_previous_hash_length", type_="check")
        batch_op.alter_column(
            "entry_hash",
            existing_type=sa.String(length=64),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "previous_hash",
            existing_type=sa.String(length=64),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
