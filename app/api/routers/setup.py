"""Setup and initialization API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.models.entity import Entity, EntityStatus, EntityType
from app.models.permission import Permission
from app.models.permissions_constants import (
    get_agent_permissions,
    get_all_permissions,
    get_investor_active_permissions,
    get_investor_pending_permissions,
    get_property_owner_permissions,
)
from app.models.role import Role
from app.models.role_assignment import RoleAssignment

router = APIRouter()
logger = logging.getLogger("app.api.setup")


@router.post(
    "/initialize-demo",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
def initialize_demo(
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Initialize demo environment with all required permissions, roles, and a demo agent.
    
    This endpoint creates:
    1. All permissions required for tokenization platform
    2. Four roles: Agent, PropertyOwner, InvestorPending, InvestorActive
    3. A demo agent user with full permissions
    
    This is idempotent - running it multiple times won't create duplicates.
    """
    logger.info("initialize_demo_started")
    
    result = {
        "permissions_created": 0,
        "roles_created": 0,
        "agent_created": False,
        "agent_id": None,
        "role_ids": {},
        "permission_ids": {},
    }
    
    # Step 1: Create all permissions
    all_permissions = get_all_permissions()
    permission_map = {}
    
    for action in all_permissions:
        existing = session.scalar(
            select(Permission).where(Permission.action == action)
        )
        
        if not existing:
            permission = Permission(action=action)
            session.add(permission)
            session.flush()
            permission_map[action] = permission.id
            result["permissions_created"] += 1
            logger.info(f"permission_created: {action}")
        else:
            permission_map[action] = existing.id
    
    session.commit()
    result["permission_ids"] = {k: str(v) for k, v in permission_map.items()}
    
    # Step 2: Create roles
    roles_config = [
        {
            "name": "Agent",
            "description": "Platform agent with full user and property management permissions",
            "scope_types": [],  # No scope restriction - can access all entity types
            "permissions": get_agent_permissions(),
        },
        {
            "name": "PropertyOwner",
            "description": "Property owner who can list and manage properties",
            "scope_types": ["issuer", "offering"],
            "permissions": get_property_owner_permissions(),
        },
        {
            "name": "InvestorPending",
            "description": "Pending investor with view-only access (before KYC approval)",
            "scope_types": ["investor", "offering"],
            "permissions": get_investor_pending_permissions(),
        },
        {
            "name": "InvestorActive",
            "description": "Active investor who can trade tokens (after KYC approval)",
            "scope_types": ["investor", "offering"],
            "permissions": get_investor_active_permissions(),
        },
    ]
    
    for role_config in roles_config:
        existing_role = session.scalar(
            select(Role).where(Role.name == role_config["name"])
        )
        
        if not existing_role:
            role = Role(
                name=role_config["name"],
                description=role_config["description"],
                scope_types=role_config["scope_types"],
                is_system=True,
            )
            session.add(role)
            session.flush()
            
            # Attach permissions
            for action in role_config["permissions"]:
                if action in permission_map:
                    permission = session.get(Permission, permission_map[action])
                    if permission:
                        role.permissions.append(permission)
            
            session.flush()
            result["roles_created"] += 1
            result["role_ids"][role_config["name"]] = str(role.id)
            logger.info(f"role_created: {role_config['name']}")
        else:
            result["role_ids"][role_config["name"]] = str(existing_role.id)
    
    session.commit()
    
    # Step 3: Create demo agent user
    existing_agent = session.scalar(
        select(Entity)
        .where(Entity.type == EntityType.AGENT)
        .where(Entity.name == "Demo Agent")
    )
    
    if not existing_agent:
        agent = Entity(
            name="Demo Agent",
            type=EntityType.AGENT,
            status=EntityStatus.ACTIVE,
            attributes={
                "email": "agent@omen-demo.com",
                "role": "platform_administrator",
            },
        )
        session.add(agent)
        session.flush()
        
        # Assign Agent role
        agent_role = session.scalar(
            select(Role).where(Role.name == "Agent")
        )
        
        if agent_role:
            assignment = RoleAssignment(
                principal_id=agent.id,
                principal_type="user",
                role_id=agent_role.id,
                entity_id=None,  # Global assignment
            )
            session.add(assignment)
        
        session.commit()
        
        result["agent_created"] = True
        result["agent_id"] = str(agent.id)
        logger.info(f"demo_agent_created: {agent.id}")
    else:
        result["agent_id"] = str(existing_agent.id)
    
    logger.info("initialize_demo_completed", extra=result)
    
    return {
        **result,
        "message": "Demo environment initialized successfully",
        "next_steps": [
            "1. Use agent_id as X-Actor-Id header for API calls",
            "2. Onboard property owners: POST /api/v1/onboarding/property-owner",
            "3. Onboard investors: POST /api/v1/onboarding/investor",
            "4. Create properties: POST /api/v1/properties",
            "5. Tokenize properties: POST /api/v1/properties/tokenize",
            "6. Activate investors: POST /api/v1/onboarding/investor/{id}/activate",
            "7. Purchase tokens: POST /api/v1/tokens/purchase",
        ],
    }


@router.post(
    "/create-sample-data",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
def create_sample_data(
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Create sample data for demo purposes.
    
    Creates:
    - 2 property owners
    - 3 investors
    - 3 properties (in various states)
    """
    logger.info("create_sample_data_started")
    
    from app.services.audit import AuditService
    
    audit = AuditService(session)
    result = {
        "owners_created": 0,
        "investors_created": 0,
        "properties_created": 0,
        "owner_ids": [],
        "investor_ids": [],
        "property_ids": [],
    }
    
    # Get roles
    property_owner_role = session.scalar(
        select(Role).where(Role.name == "PropertyOwner")
    )
    investor_pending_role = session.scalar(
        select(Role).where(Role.name == "InvestorPending")
    )
    
    # Create property owners
    owners_data = [
        {
            "name": "Luxury Real Estate LLC",
            "company_name": "Luxury Real Estate LLC",
            "email": "owner@luxuryrealestate.com",
        },
        {
            "name": "Downtown Properties Inc",
            "company_name": "Downtown Properties Inc",
            "email": "owner@downtownproperties.com",
        },
    ]
    
    for owner_data in owners_data:
        owner = Entity(
            name=owner_data["name"],
            type=EntityType.ISSUER,
            status=EntityStatus.ACTIVE,
            attributes={
                "company_name": owner_data["company_name"],
                "contact_email": owner_data["email"],
                "onboarding_status": "completed",
                "kyc_status": "approved",
            },
        )
        session.add(owner)
        session.flush()
        
        if property_owner_role:
            assignment = RoleAssignment(
                principal_id=owner.id,
                principal_type="user",
                role_id=property_owner_role.id,
                entity_id=owner.id,
            )
            session.add(assignment)
        
        result["owners_created"] += 1
        result["owner_ids"].append(str(owner.id))
    
    session.commit()
    
    # Create investors
    investors_data = [
        {"name": "John Investor", "email": "john@investor.com", "type": "individual"},
        {"name": "Jane Doe", "email": "jane@doe.com", "type": "individual"},
        {"name": "Institutional Fund LLC", "email": "fund@institution.com", "type": "institutional"},
    ]
    
    for investor_data in investors_data:
        investor = Entity(
            name=investor_data["name"],
            type=EntityType.INVESTOR,
            status=EntityStatus.ACTIVE,
            attributes={
                "email": investor_data["email"],
                "investor_type": investor_data["type"],
                "kyc_status": "pending",
                "onboarding_status": "pending",
                "token_holdings": {},
            },
        )
        session.add(investor)
        session.flush()
        
        if investor_pending_role:
            assignment = RoleAssignment(
                principal_id=investor.id,
                principal_type="user",
                role_id=investor_pending_role.id,
                entity_id=None,
            )
            session.add(assignment)
        
        result["investors_created"] += 1
        result["investor_ids"].append(str(investor.id))
    
    session.commit()
    
    # Create properties
    owner_id = UUID(result["owner_ids"][0]) if result["owner_ids"] else None
    
    if owner_id:
        properties_data = [
            {
                "name": "Sunset Boulevard Apartments",
                "type": "residential",
                "address": "123 Sunset Blvd, Los Angeles, CA 90028",
                "valuation": 5000000,
                "total_tokens": 50000,
                "token_price": 100,
            },
            {
                "name": "Downtown Office Tower",
                "type": "commercial",
                "address": "456 Main St, New York, NY 10001",
                "valuation": 15000000,
                "total_tokens": 150000,
                "token_price": 100,
            },
            {
                "name": "Waterfront Condos",
                "type": "residential",
                "address": "789 Beach Rd, Miami, FL 33139",
                "valuation": 8000000,
                "total_tokens": 80000,
                "token_price": 100,
            },
        ]
        
        for prop_data in properties_data:
            property_entity = Entity(
                name=prop_data["name"],
                type=EntityType.OFFERING,
                status=EntityStatus.ACTIVE,
                parent_id=owner_id,
                attributes={
                    "property_type": prop_data["type"],
                    "address": prop_data["address"],
                    "valuation": prop_data["valuation"],
                    "total_tokens": prop_data["total_tokens"],
                    "token_price": prop_data["token_price"],
                    "available_tokens": prop_data["total_tokens"],
                    "property_status": "pending",
                    "minimum_investment": 1000,
                },
            )
            session.add(property_entity)
            session.flush()
            
            result["properties_created"] += 1
            result["property_ids"].append(str(property_entity.id))
        
        session.commit()
    
    logger.info("create_sample_data_completed", extra=result)
    
    return {
        **result,
        "message": "Sample data created successfully",
    }


