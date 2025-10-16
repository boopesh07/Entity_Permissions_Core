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
