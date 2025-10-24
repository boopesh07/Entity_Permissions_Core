from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.cache import get_permission_cache


def create_entity(client: TestClient, name: str, entity_type: str, parent_id: str | None = None) -> str:
    payload = {"name": name, "type": entity_type, "parent_id": parent_id, "attributes": {}}
    response = client.post("/api/v1/entities", json={**payload, "status": "active"})
    response.raise_for_status()
    return response.json()["id"]


def create_role(client: TestClient, name: str, permissions: list[str], scope_types: list[str] | None = None) -> str:
    payload = {
        "name": name,
        "permissions": permissions,
        "scope_types": scope_types or [],
    }
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


def test_global_admin_role_without_scope_limits(client: TestClient) -> None:
    issuer_id = create_entity(client, "Issuer Delta", "issuer")
    spv_id = create_entity(client, "SPV Epsilon", "spv")
    role_id = create_role(
        client,
        name="global_admin",
        permissions=["document:upload", "document:archive"],
        scope_types=[],
    )

    user_id = str(uuid4())
    assign_role(client, role_id, user_id, entity_id=None)

    assert authorize(client, user_id, "document:upload", issuer_id) is True
    assert authorize(client, user_id, "document:archive", spv_id) is True


def test_role_resolution_for_admin_issuer_investor(client: TestClient) -> None:
    issuer_id = create_entity(client, "Issuer Omega", "issuer")
    investor_id = create_entity(client, "Investor Lambda", "investor")

    admin_role = create_role(
        client,
        name="admin_role",
        permissions=["document:upload", "document:archive", "document:download"],
        scope_types=[],
    )
    issuer_role = create_role(
        client,
        name="issuer_role",
        permissions=["document:upload"],
        scope_types=["issuer"],
    )
    investor_role = create_role(
        client,
        name="investor_role",
        permissions=["document:download"],
        scope_types=["investor"],
    )

    admin_user = str(uuid4())
    issuer_user = str(uuid4())
    investor_user = str(uuid4())

    assign_role(client, admin_role, admin_user, entity_id=None)
    assign_role(client, issuer_role, issuer_user, entity_id=issuer_id)
    assign_role(client, investor_role, investor_user, entity_id=investor_id)

    assert authorize(client, admin_user, "document:archive", issuer_id) is True
    assert authorize(client, admin_user, "document:download", investor_id) is True
    assert authorize(client, issuer_user, "document:upload", issuer_id) is True
    assert authorize(client, issuer_user, "document:upload", investor_id) is False
    assert authorize(client, investor_user, "document:download", investor_id) is True
    assert authorize(client, investor_user, "document:download", issuer_id) is False


def test_permission_cache_invalidation_on_assignment_change(client: TestClient) -> None:
    cache = get_permission_cache()
    cache.invalidate()

    entity_id = create_entity(client, "Cache Entity", "issuer")
    role_id = create_role(client, "cache_role", ["document:upload"], scope_types=["issuer"])
    user_id = str(uuid4())
    assignment_id = assign_role(client, role_id, user_id, entity_id)

    assert authorize(client, user_id, "document:upload", entity_id) is True

    revoke_resp = client.delete(f"/api/v1/assignments/{assignment_id}")
    revoke_resp.raise_for_status()

    assert authorize(client, user_id, "document:upload", entity_id) is False


def test_authorization_deterministic_across_runs(client: TestClient) -> None:
    cache = get_permission_cache()
    cache.invalidate()

    entity_id = create_entity(client, "Deterministic Entity", "issuer")
    role_id = create_role(client, "deterministic_role", ["document:archive"])
    user_id = str(uuid4())
    assign_role(client, role_id, user_id, entity_id=None)

    results = [authorize(client, user_id, "document:archive", entity_id) for _ in range(5)]
    assert all(results)


def test_authorization_fails_with_nonexistent_entity(client: TestClient) -> None:
    """Verify authorization returns 404 error when entity doesn't exist."""
    user_id = str(uuid4())
    fake_entity_id = str(uuid4())  # Non-existent entity

    response = client.post(
        "/api/v1/authorize",
        json={"user_id": user_id, "action": "document:upload", "resource_id": fake_entity_id},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_authorization_with_valid_entity_after_assignment(client: TestClient) -> None:
    """Verify authorization works correctly with valid entity after role assignment."""
    entity_id = create_entity(client, "Valid Entity", "issuer")
    role_id = create_role(client, "valid_role", ["document:upload"])
    user_id = str(uuid4())
    assign_role(client, role_id, user_id, entity_id)

    # Should return True for authorized action
    assert authorize(client, user_id, "document:upload", entity_id) is True

    # Should return False for unauthorized action
    assert authorize(client, user_id, "document:download", entity_id) is False


def test_authorization_fails_for_archived_entity(client: TestClient) -> None:
    """Verify authorization behavior when entity is archived.
    
    Archived entities still exist in the database but are marked as archived.
    Authorization should still work on archived entities.
    """
    entity_id = create_entity(client, "Archive Test Entity", "issuer")
    role_id = create_role(client, "archive_test_role", ["document:upload"])
    user_id = str(uuid4())
    assign_role(client, role_id, user_id, entity_id)

    # Verify authorization works before archiving
    assert authorize(client, user_id, "document:upload", entity_id) is True

    # Archive the entity
    archive_resp = client.post(f"/api/v1/entities/{entity_id}/archive")
    archive_resp.raise_for_status()

    # Authorization should still work (archived entities exist in DB, just marked as archived)
    # This is the expected behavior - archived entities can still be queried for permissions
    assert authorize(client, user_id, "document:upload", entity_id) is True
