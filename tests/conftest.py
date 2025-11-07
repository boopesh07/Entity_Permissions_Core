import os
import sys
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("EPR_ENVIRONMENT", "test")
os.environ.setdefault("EPR_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("EPR_REDIS_URL", "")
os.environ.setdefault("EPR_REDIS_TOKEN", "")
os.environ.setdefault("EPR_DOCUMENT_VAULT_TOPIC_ARN", "")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.database import engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402
from app.events_engine.dispatcher import EventDispatcher, set_event_dispatcher  # noqa: E402
from app.events_engine.publisher import NullEventPublisher  # noqa: E402
from app.services import cache as cache_module  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache_module._shared_cache = cache_module.InMemoryPermissionCache()
    set_event_dispatcher(
        EventDispatcher(publisher=NullEventPublisher(), default_source="entity_permissions_core", max_attempts=2)
    )
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:  # noqa: ANN001
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def event_dispatcher_stub(monkeypatch):
    from app.events_engine import dispatcher as dispatcher_module

    class StubPublisher:
        def __init__(self) -> None:
            self.envelopes = []

        def publish(self, envelope):
            self.envelopes.append(envelope)

    publisher = StubPublisher()
    dispatcher = EventDispatcher(publisher=publisher, default_source="entity_permissions_core", max_attempts=2)
    dispatcher.stub_publisher = publisher  # type: ignore[attr-defined]
    dispatcher_module.set_event_dispatcher(dispatcher)
    yield dispatcher
    dispatcher_module.set_event_dispatcher(
        EventDispatcher(publisher=NullEventPublisher(), default_source="entity_permissions_core", max_attempts=2)
    )
warnings.filterwarnings("ignore", category=PendingDeprecationWarning, module="starlette.formparsers")
