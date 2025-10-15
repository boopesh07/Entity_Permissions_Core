"""Role model for grouping permissions."""

from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.types import GUID, JSONType


class Role(TimestampMixin, Base):
    """Composable role linking to permissions and assignments."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("name", name="uq_roles_name"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(length=120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(length=512), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scope_types: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)

    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )
    assignments: Mapped[List["RoleAssignment"]] = relationship(
        "RoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
    )
