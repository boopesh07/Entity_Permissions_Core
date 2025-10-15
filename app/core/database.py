"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


def _resolve_sqlite_path(database_url: str) -> None:
    """Ensure the parent directory for a SQLite database exists."""

    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        return

    if parsed.path in (":memory:", "/:memory:"):
        return

    # Handles relative paths such as sqlite:///./data/epr.db
    if parsed.path.startswith("/"):
        db_path = Path(parsed.path)
    else:
        db_path = Path(parsed.path)
    db_dir = db_path.expanduser().resolve().parent
    db_dir.mkdir(parents=True, exist_ok=True)


def _create_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        _resolve_sqlite_path(url)
        connect_args = {"check_same_thread": False}
        engine_kwargs: dict[str, object] = {
            "future": True,
            "echo": settings.sql_echo,
            "connect_args": connect_args,
        }
        if url.endswith(":memory:") or url == "sqlite://":
            engine_kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **engine_kwargs)
    else:
        engine = create_engine(
            url,
            future=True,
            echo=settings.sql_echo,
            pool_pre_ping=True,
        )
    return engine


engine: Engine = _create_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
    class_=Session,
)


def get_session() -> Iterator[Session]:
    """FastAPI dependency for acquiring a database session."""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope for scripts and background jobs."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
