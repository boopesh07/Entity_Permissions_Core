from __future__ import annotations

from fastapi.testclient import TestClient


def test_entity_lifecycle(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/entities",
        json={"name": "Issuer Beta", "type": "issuer", "attributes": {"country": "US"}, "status": "active"},
    )
    create_resp.raise_for_status()
    entity = create_resp.json()

    update_resp = client.patch(
        f"/api/v1/entities/{entity['id']}",
        json={"name": "Issuer Beta Updated", "attributes": {"country": "CA"}},
    )
    update_resp.raise_for_status()
    updated_entity = update_resp.json()
    assert updated_entity["name"] == "Issuer Beta Updated"
    assert updated_entity["attributes"]["country"] == "CA"

    list_resp = client.get("/api/v1/entities")
    list_resp.raise_for_status()
    entities = list_resp.json()
    assert any(item["id"] == entity["id"] for item in entities)

    archive_resp = client.post(f"/api/v1/entities/{entity['id']}/archive")
    archive_resp.raise_for_status()
    archived_entity = archive_resp.json()
    assert archived_entity["status"] == "archived"


def test_entity_duplicate_conflict(client: TestClient) -> None:
    payload = {"name": "Issuer Gamma", "type": "issuer", "attributes": {}, "status": "active"}

    first = client.post("/api/v1/entities", json=payload)
    first.raise_for_status()

    duplicate = client.post("/api/v1/entities", json=payload)
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_entity_invalid_payload_returns_400(client: TestClient) -> None:
    response = client.post("/api/v1/entities", json={"type": "issuer"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(error["loc"][-1] == "name" for error in detail)


def test_entity_immutable_fields_rejected(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/entities",
        json={"name": "Immutable Check", "type": "issuer", "attributes": {}, "status": "active"},
    )
    create_resp.raise_for_status()
    entity_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/entities/{entity_id}", json={"type": "spv"})
    assert patch_resp.status_code == 400

    get_resp = client.get(f"/api/v1/entities/{entity_id}")
    get_resp.raise_for_status()
    assert get_resp.json()["type"] == "issuer"


def test_archived_entities_hidden_from_list(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/entities",
        json={"name": "Archived Entity", "type": "issuer", "attributes": {}, "status": "active"},
    )
    create_resp.raise_for_status()
    entity_id = create_resp.json()["id"]

    archive_resp = client.post(f"/api/v1/entities/{entity_id}/archive")
    archive_resp.raise_for_status()

    list_resp = client.get("/api/v1/entities")
    list_resp.raise_for_status()
    ids = [item["id"] for item in list_resp.json()]
    assert entity_id not in ids


def test_entity_archive_publishes_document_event(client: TestClient, document_publisher_stub) -> None:
    create_resp = client.post(
        "/api/v1/entities",
        json={"name": "Document Event", "type": "issuer", "attributes": {}, "status": "active"},
    )
    create_resp.raise_for_status()
    entity_id = create_resp.json()["id"]

    archive_resp = client.post(f"/api/v1/entities/{entity_id}/archive")
    archive_resp.raise_for_status()

    assert len(document_publisher_stub.deleted_events) == 1
    event = document_publisher_stub.deleted_events[0]
    assert event["entity_id"] == entity_id
    assert event["entity_type"] == "issuer"
