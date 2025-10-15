"""Role assignment linking principals to entities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.types import GUID


class RoleAssignment(TimestampMixin, Base):
    """Assigns a role to a principal for an entity."""

    __tablename__ = "role_assignments"
    __table_args__ = (
        Index("ix_role_assignments_principal", "principal_id"),
        Index("ix_role_assignments_entity", "entity_id"),
        Index("ix_role_assignments_role", "role_id"),
        UniqueConstraint("principal_id", "principal_type", "role_id", "entity_id", name="uq_role_assignments_principal_role_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    principal_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(length=64), nullable=False, default="user")
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    entity: Mapped[Optional["Entity"]] = relationship("Entity")
    role: Mapped["Role"] = relationship("Role", back_populates="assignments")
