"""Tests for tokenization workflows and token operations."""

from __future__ import annotations

from fastapi.testclient import TestClient


def setup_demo_environment(client: TestClient) -> dict:
    """Setup demo environment and return key IDs."""
    init_response = client.post("/api/v1/setup/initialize-demo")
    init_response.raise_for_status()
    return init_response.json()


def test_initialize_demo(client: TestClient) -> None:
    """Test demo initialization creates all required setup."""
    response = client.post("/api/v1/setup/initialize-demo")
    response.raise_for_status()
    
    data = response.json()
    assert data["permissions_created"] >= 0
    assert data["roles_created"] >= 0
    assert data["agent_id"] is not None
    assert "Agent" in data["role_ids"]
    assert "PropertyOwner" in data["role_ids"]
    assert "InvestorPending" in data["role_ids"]
    assert "InvestorActive" in data["role_ids"]


def test_onboard_property_owner(client: TestClient) -> None:
    """Test property owner onboarding."""
    demo = setup_demo_environment(client)
    agent_id = demo["agent_id"]
    
    response = client.post(
        "/api/v1/onboarding/property-owner",
        json={
            "name": "Real Estate Holdings",
            "company_name": "Real Estate Holdings LLC",
            "contact_email": "contact@reholdings.com",
            "phone": "+1234567890",
        },
        headers={"X-Actor-Id": agent_id},
    )
    response.raise_for_status()
    
    data = response.json()
    assert data["entity_type"] == "issuer"
    assert data["role_assigned"] is True
    assert data["onboarding_status"] == "completed"


def test_onboard_investor(client: TestClient) -> None:
    """Test investor onboarding."""
    demo = setup_demo_environment(client)
    agent_id = demo["agent_id"]
    
    response = client.post(
        "/api/v1/onboarding/investor",
        json={
            "name": "Alice Investor",
            "email": "alice@investor.com",
            "investor_type": "individual",
        },
        headers={"X-Actor-Id": agent_id},
    )
    response.raise_for_status()
    
    data = response.json()
    assert data["entity_type"] == "investor"
    assert data["role_assigned"] is True
    assert data["onboarding_status"] == "pending"


def test_get_token_details(client: TestClient) -> None:
    """Test getting token details for a property."""
    demo = setup_demo_environment(client)
    agent_id = demo["agent_id"]
    
    # Create owner and property
    owner_response = client.post(
        "/api/v1/onboarding/property-owner",
        json={
            "name": "Token Test Owner",
            "company_name": "Token Test LLC",
            "contact_email": "token@test.com",
        },
        headers={"X-Actor-Id": agent_id},
    )
    owner_id = owner_response.json()["entity_id"]
    
    property_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Tokenized Property",
            "owner_id": owner_id,
            "property_type": "residential",
            "address": "123 Token St",
            "valuation": 3000000,
            "total_tokens": 30000,
            "token_price": 100,
        },
        headers={"X-Actor-Id": agent_id},
    )
    property_id = property_response.json()["id"]
    
    # Get token details
    response = client.get(f"/api/v1/tokens/{property_id}")
    response.raise_for_status()
    
    token_data = response.json()
    assert token_data["property_name"] == "Tokenized Property"
    assert token_data["total_tokens"] == 30000
    assert token_data["token_price"] == 100.0
    assert token_data["available_tokens"] == 30000


def test_create_sample_data(client: TestClient) -> None:
    """Test creating sample data for demo."""
    # Initialize first
    setup_demo_environment(client)
    
    response = client.post("/api/v1/setup/create-sample-data")
    response.raise_for_status()
    
    data = response.json()
    assert data["owners_created"] == 2
    assert data["investors_created"] == 3
    assert data["properties_created"] == 3
    assert len(data["owner_ids"]) == 2
    assert len(data["investor_ids"]) == 3
    assert len(data["property_ids"]) == 3


def test_property_owner_role_permissions(client: TestClient) -> None:
    """Test that property owner has correct permissions."""
    demo = setup_demo_environment(client)
    agent_id = demo["agent_id"]
    
    # Create property owner
    owner_response = client.post(
        "/api/v1/onboarding/property-owner",
        json={
            "name": "Permission Test Owner",
            "company_name": "Permission Test LLC",
            "contact_email": "perm@test.com",
        },
        headers={"X-Actor-Id": agent_id},
    )
    owner_id = owner_response.json()["entity_id"]
    
    # Owner should be able to create properties
    property_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Owner's Property",
            "owner_id": owner_id,
            "property_type": "residential",
            "address": "456 Permission Ave",
            "valuation": 2000000,
            "total_tokens": 20000,
            "token_price": 100,
        },
        headers={"X-Actor-Id": owner_id},
    )
    assert property_response.status_code == 201


def test_investor_pending_cannot_purchase(client: TestClient) -> None:
    """Test that pending investor cannot purchase tokens."""
    demo = setup_demo_environment(client)
    agent_id = demo["agent_id"]
    
    # Create investor (pending)
    investor_response = client.post(
        "/api/v1/onboarding/investor",
        json={
            "name": "Pending Investor",
            "email": "pending@investor.com",
            "investor_type": "individual",
        },
        headers={"X-Actor-Id": agent_id},
    )
    investor_id = investor_response.json()["entity_id"]
    
    # Create owner and property
    owner_response = client.post(
        "/api/v1/onboarding/property-owner",
        json={
            "name": "Purchase Test Owner",
            "company_name": "Purchase Test LLC",
            "contact_email": "purchase@test.com",
        },
        headers={"X-Actor-Id": agent_id},
    )
    owner_id = owner_response.json()["entity_id"]
    
    property_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Test Purchase Property",
            "owner_id": owner_id,
            "property_type": "commercial",
            "address": "789 Purchase Blvd",
            "valuation": 5000000,
            "total_tokens": 50000,
            "token_price": 100,
        },
        headers={"X-Actor-Id": agent_id},
    )
    property_id = property_response.json()["id"]
    
    # Try to purchase tokens (should fail validation)
    purchase_response = client.post(
        "/api/v1/tokens/purchase",
        json={
            "investor_id": investor_id,
            "property_id": property_id,
            "token_quantity": 10,
            "payment_method": "card",
        },
        headers={"X-Actor-Id": investor_id},
    )
    
    # Should return 202 but with failed status
    assert purchase_response.status_code == 202
    purchase_data = purchase_response.json()
    assert purchase_data["status"] in ["failed", "skipped"]



