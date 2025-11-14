"""Tests for property management endpoints."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def create_agent(client: TestClient) -> str:
    """Initialize demo and return agent ID."""
    response = client.post("/api/v1/setup/initialize-demo")
    response.raise_for_status()
    return response.json()["agent_id"]


def create_property_owner(client: TestClient, agent_id: str) -> str:
    """Create a property owner."""
    response = client.post(
        "/api/v1/onboarding/property-owner",
        json={
            "name": "Test Owner LLC",
            "company_name": "Test Owner LLC",
            "contact_email": "owner@test.com",
        },
        headers={"X-Actor-Id": agent_id},
    )
    response.raise_for_status()
    return response.json()["entity_id"]


def test_create_property(client: TestClient) -> None:
    """Test creating a property."""
    agent_id = create_agent(client)
    owner_id = create_property_owner(client, agent_id)
    
    response = client.post(
        "/api/v1/properties",
        json={
            "name": "Test Property",
            "owner_id": owner_id,
            "property_type": "residential",
            "address": "123 Test St",
            "valuation": 1000000,
            "total_tokens": 10000,
            "token_price": 100,
            "minimum_investment": 1000,
        },
        headers={"X-Actor-Id": agent_id},
    )
    response.raise_for_status()
    
    property_data = response.json()
    assert property_data["name"] == "Test Property"
    assert property_data["property_type"] == "residential"
    assert property_data["total_tokens"] == 10000
    assert property_data["property_status"] == "pending"


def test_list_properties(client: TestClient) -> None:
    """Test listing properties."""
    agent_id = create_agent(client)
    owner_id = create_property_owner(client, agent_id)
    
    # Create two properties
    for i in range(2):
        client.post(
            "/api/v1/properties",
            json={
                "name": f"Property {i}",
                "owner_id": owner_id,
                "property_type": "residential",
                "address": f"{i} Test St",
                "valuation": 1000000,
                "total_tokens": 10000,
                "token_price": 100,
            },
            headers={"X-Actor-Id": agent_id},
        )
    
    response = client.get("/api/v1/properties")
    response.raise_for_status()
    
    data = response.json()
    assert data["total"] >= 2
    assert len(data["properties"]) >= 2


def test_get_property(client: TestClient) -> None:
    """Test getting property details."""
    agent_id = create_agent(client)
    owner_id = create_property_owner(client, agent_id)
    
    create_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Specific Property",
            "owner_id": owner_id,
            "property_type": "commercial",
            "address": "456 Business Ave",
            "valuation": 5000000,
            "total_tokens": 50000,
            "token_price": 100,
        },
        headers={"X-Actor-Id": agent_id},
    )
    property_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/properties/{property_id}")
    response.raise_for_status()
    
    property_data = response.json()
    assert property_data["id"] == property_id
    assert property_data["name"] == "Specific Property"
    assert property_data["property_type"] == "commercial"


def test_update_property(client: TestClient) -> None:
    """Test updating property details."""
    agent_id = create_agent(client)
    owner_id = create_property_owner(client, agent_id)
    
    create_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Original Name",
            "owner_id": owner_id,
            "property_type": "residential",
            "address": "789 Update St",
            "valuation": 2000000,
            "total_tokens": 20000,
            "token_price": 100,
        },
        headers={"X-Actor-Id": agent_id},
    )
    property_id = create_response.json()["id"]
    
    response = client.patch(
        f"/api/v1/properties/{property_id}",
        json={
            "name": "Updated Name",
            "valuation": 2500000,
        },
        headers={"X-Actor-Id": agent_id},
    )
    response.raise_for_status()
    
    updated_data = response.json()
    assert updated_data["name"] == "Updated Name"
    assert updated_data["valuation"] == 2500000


def test_filter_properties_by_status(client: TestClient) -> None:
    """Test filtering properties by status."""
    agent_id = create_agent(client)
    owner_id = create_property_owner(client, agent_id)
    
    client.post(
        "/api/v1/properties",
        json={
            "name": "Pending Property",
            "owner_id": owner_id,
            "property_type": "residential",
            "address": "111 Pending St",
            "valuation": 1000000,
            "total_tokens": 10000,
            "token_price": 100,
        },
        headers={"X-Actor-Id": agent_id},
    )
    
    response = client.get("/api/v1/properties?status=pending")
    response.raise_for_status()
    
    data = response.json()
    assert data["total"] >= 1
    for prop in data["properties"]:
        assert prop["property_status"] == "pending"



