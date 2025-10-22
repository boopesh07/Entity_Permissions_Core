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
from app.services import cache as cache_module  # noqa: E402
from app.services import notifications  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache_module._shared_cache = cache_module.InMemoryPermissionCache()
    notifications._publisher = notifications.NullDocumentVaultPublisher()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def document_publisher_stub(monkeypatch):
    class StubPublisher:
        def __init__(self) -> None:
            self.deleted_events = []

        def publish_entity_deleted(self, *, entity_id, entity_type) -> None:
            self.deleted_events.append({"entity_id": str(entity_id), "entity_type": entity_type})

        def invalidate(self) -> None:
            self.deleted_events.clear()

    stub = StubPublisher()
    monkeypatch.setattr(notifications, "get_document_publisher", lambda: stub)
    return stub


@pytest.fixture()
def client(document_publisher_stub) -> TestClient:  # noqa: ANN001
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
warnings.filterwarnings("ignore", category=PendingDeprecationWarning, module="starlette.formparsers")
