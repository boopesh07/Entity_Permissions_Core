from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def create_entity(client: TestClient, name: str, entity_type: str, parent_id: str | None = None) -> str:
    payload = {"name": name, "type": entity_type, "parent_id": parent_id, "attributes": {}}
    response = client.post("/api/v1/entities", json={**payload, "status": "active"})
    response.raise_for_status()
    return response.json()["id"]


def create_role(client: TestClient, name: str, permissions: list[str]) -> str:
    payload = {"name": name, "permissions": permissions, "scope_types": []}
    response = client.post("/api/v1/roles", json=payload)
    response.raise_for_status()
    return response.json()["id"]


def assign_role(client: TestClient, role_id: str, principal_id: str, entity_id: str | None = None) -> str:
    payload = {
        "role_id": role_id,
        "principal_id": principal_id,
        "entity_id": entity_id,
        "principal_type": "user",
    }
    response = client.post("/api/v1/assignments", json=payload)
    response.raise_for_status()
    return response.json()["id"]


def authorize(client: TestClient, user_id: str, action: str, resource_id: str) -> bool:
    response = client.post("/api/v1/authorize", json={"user_id": user_id, "action": action, "resource_id": resource_id})
    response.raise_for_status()
    return response.json()["authorized"]


def test_authorization_grants_for_direct_assignment(client: TestClient) -> None:
    entity_id = create_entity(client, "Issuing Entity", "issuer")
    role_id = create_role(client, "issuer_admin", ["document:upload"])

    user_id = str(uuid4())
    assign_role(client, role_id, user_id, entity_id)

    assert authorize(client, user_id, "document:upload", entity_id) is True
    assert authorize(client, user_id, "document:download", entity_id) is False


def test_authorization_inherits_from_parent_entity(client: TestClient) -> None:
    issuer_id = create_entity(client, "Issuer", "issuer")
    offering_id = create_entity(client, "Offering", "offering", parent_id=issuer_id)
    role_id = create_role(client, "issuer_doc_admin", ["document:upload", "document:verify"])

    user_id = str(uuid4())
    assign_role(client, role_id, user_id, issuer_id)

    assert authorize(client, user_id, "document:upload", offering_id) is True
    assert authorize(client, user_id, "document:verify", offering_id) is True


def test_authorization_denied_without_assignment(client: TestClient) -> None:
    entity_id = create_entity(client, "SPV", "spv")
    user_id = str(uuid4())

    assert authorize(client, user_id, "document:upload", entity_id) is False
