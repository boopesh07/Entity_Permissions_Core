"""Entity model representing issuers, offerings, investors, etc."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.types import GUID, JSONType


class EntityType(str, Enum):
    ISSUER = "issuer"
    SPV = "spv"
    OFFERING = "offering"
    INVESTOR = "investor"
    AGENT = "agent"
    OTHER = "other"


class EntityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Entity(TimestampMixin, Base):
    """Core entity model stored in the registry."""

    __tablename__ = "entities"
    __table_args__ = (
        Index("ix_entities_type", "type"),
        Index("ix_entities_parent", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    type: Mapped[EntityType] = mapped_column(SqlEnum(EntityType, name="entity_type"), nullable=False)
    status: Mapped[EntityStatus] = mapped_column(
        SqlEnum(EntityStatus, name="entity_status"),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    attributes: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    parent: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        remote_side="Entity.id",
        back_populates="children",
    )
    children: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
