"""Declarative base and mixins."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


class TimestampMixin:
    """Adds created_at/updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        default=None,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=None,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
