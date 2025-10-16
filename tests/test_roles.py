from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_role_scope_validation(client: TestClient) -> None:
    # Create role limited to issuer entities
    role_payload = {"name": "issuer_only", "permissions": ["document:upload"], "scope_types": ["issuer"]}
    role_resp = client.post("/api/v1/roles", json=role_payload)
    role_resp.raise_for_status()
    role_id = role_resp.json()["id"]

    # Create SPV entity
    entity_resp = client.post(
        "/api/v1/entities",
        json={"name": "SPV Alpha", "type": "spv", "attributes": {}, "status": "active"},
    )
    entity_resp.raise_for_status()
    entity_id = entity_resp.json()["id"]

    user_id = str(uuid4())
    assignment_resp = client.post(
        "/api/v1/assignments",
        json={
            "principal_id": user_id,
            "role_id": role_id,
            "entity_id": entity_id,
            "principal_type": "user",
        },
    )
    assert assignment_resp.status_code == 400
    assert assignment_resp.json()["detail"].startswith("Role issuer_only cannot be assigned")


def test_role_listing_returns_permissions(client: TestClient) -> None:
    role_payload = {"name": "viewer", "permissions": ["document:download"], "scope_types": []}
    response = client.post("/api/v1/roles", json=role_payload)
    response.raise_for_status()

    list_resp = client.get("/api/v1/roles")
    list_resp.raise_for_status()
    roles = list_resp.json()
    assert roles
    created_role = next(role for role in roles if role["name"] == "viewer")
    assert "document:download" in created_role["permissions"]


def test_role_assignment_idempotent_and_listing(client: TestClient) -> None:
    role_resp = client.post(
        "/api/v1/roles",
        json={"name": "doc_uploader", "permissions": ["document:upload"], "scope_types": []},
    )
    role_resp.raise_for_status()
    role_id = role_resp.json()["id"]

    entity_resp = client.post(
        "/api/v1/entities",
        json={"name": "Issuer Zeta", "type": "issuer", "attributes": {}, "status": "active"},
    )
    entity_resp.raise_for_status()
    entity_id = entity_resp.json()["id"]

    user_id = str(uuid4())
    assign_one = client.post(
        "/api/v1/assignments",
        json={"principal_id": user_id, "role_id": role_id, "entity_id": entity_id, "principal_type": "user"},
    )
    assign_one.raise_for_status()
    assignment_id = assign_one.json()["id"]

    assign_two = client.post(
        "/api/v1/assignments",
        json={"principal_id": user_id, "role_id": role_id, "entity_id": entity_id, "principal_type": "user"},
    )
    assign_two.raise_for_status()
    assert assign_two.json()["id"] == assignment_id

    list_resp = client.get("/api/v1/assignments", params={"principal_id": user_id})
    list_resp.raise_for_status()
    assignments = list_resp.json()
    assert len(assignments) == 1


def test_role_update_and_revoke_assignment(client: TestClient) -> None:
    role_resp = client.post(
        "/api/v1/roles",
        json={"name": "doc_manager", "permissions": ["document:upload"], "scope_types": []},
    )
    role_resp.raise_for_status()
    role_id = role_resp.json()["id"]

    update_resp = client.patch(
        f"/api/v1/roles/{role_id}",
        json={"description": "Document manager", "permissions": ["document:upload", "document:verify"]},
    )
    update_resp.raise_for_status()
    updated_role = update_resp.json()
    assert updated_role["description"] == "Document manager"
    assert set(updated_role["permissions"]) == {"document:upload", "document:verify"}

    entity_resp = client.post(
        "/api/v1/entities",
        json={"name": "Issuer Theta", "type": "issuer", "attributes": {}, "status": "active"},
    )
    entity_resp.raise_for_status()
    entity_id = entity_resp.json()["id"]

    user_id = str(uuid4())
    assignment_resp = client.post(
        "/api/v1/assignments",
        json={"principal_id": user_id, "role_id": role_id, "entity_id": entity_id, "principal_type": "user"},
    )
    assignment_resp.raise_for_status()
    assignment_id = assignment_resp.json()["id"]

    revoke_resp = client.delete(f"/api/v1/assignments/{assignment_id}")
    revoke_resp.raise_for_status()
    assert revoke_resp.json()["status"] == "revoked"

    list_resp = client.get("/api/v1/assignments", params={"principal_id": user_id})
    list_resp.raise_for_status()
    assert list_resp.json() == []


def test_role_duplicate_conflict(client: TestClient) -> None:
    payload = {"name": "issuer-doc-admin", "permissions": ["document:upload"], "scope_types": ["issuer"]}

    first = client.post("/api/v1/roles", json=payload)
    first.raise_for_status()

    duplicate = client.post("/api/v1/roles", json=payload)
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]
