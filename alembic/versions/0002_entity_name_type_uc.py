"""Add unique constraint on entity name/type."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0002_entity_name_type_uc"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_entities_name_type", "entities", ["name", "type"])


def downgrade() -> None:
    op.drop_constraint("uq_entities_name_type", "entities", type_="unique")
