"""Permission model representing atomic actions."""

from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.types import GUID


class Permission(TimestampMixin, Base):
    """Atomic permission identified by an action string."""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("action", name="uq_permissions_action"),
        Index("ix_permissions_action", "action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(length=255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )
