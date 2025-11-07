"""Dependency injection helpers for FastAPI routes."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.events_engine import get_event_dispatcher
from app.events_engine.service import EventService
from app.services.authorization import AuthorizationService
from app.services.cache import get_permission_cache
from app.services.entities import EntityService
from app.services.roles import RoleService


def get_db_session() -> Session:
    yield from get_session()


def get_entity_service(session: Session = Depends(get_db_session)) -> EntityService:
    return EntityService(session, event_dispatcher=get_event_dispatcher())


def get_role_service(session: Session = Depends(get_db_session)) -> RoleService:
    cache = get_permission_cache()
    return RoleService(session, cache=cache)


def get_authorization_service(session: Session = Depends(get_db_session)) -> AuthorizationService:
    cache = get_permission_cache()
    return AuthorizationService(session, cache=cache)


def get_event_service(session: Session = Depends(get_db_session)) -> EventService:
    return EventService(session, dispatcher=get_event_dispatcher())
