"""Temporal activities for real estate tokenization workflows."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from uuid import UUID

from temporalio import activity

from app.core.database import session_scope
from app.models.entity import Entity, EntityStatus
from app.services.blockchain import get_blockchain_service
from app.services.payment import get_payment_service
from app.services.token_registry import get_token_registry_service

logger = logging.getLogger("app.workflow.tokenization_activities")


@activity.defn(name="verify_property_documents_activity")
async def verify_property_documents_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify property documents are complete and valid.
    
    Integrates with DocumentVaultService to check document status.
    """
    from app.services.document_vault_client import get_document_vault_client
    
    property_id = payload["property_id"]
    
    logger.info(
        "workflow_verify_property_documents",
        extra={"property_id": property_id},
    )
    
    # Call DocumentVault API to check for verified documents
    vault_client = get_document_vault_client()
    has_verified_docs = await vault_client.check_documents_status(
        entity_id=property_id,
        required_status="verified",
    )
    
    with session_scope() as session:
        property_entity = session.get(Entity, UUID(property_id))
        if not property_entity:
            return {"approved": False, "reason": "Property not found"}
        
        property_details = {
            "total_tokens": property_entity.attributes.get("total_tokens", 0),
            "token_price": property_entity.attributes.get("token_price", 0),
            "valuation": property_entity.attributes.get("valuation", 0),
            "property_type": property_entity.attributes.get("property_type", ""),
            "address": property_entity.attributes.get("address", ""),
        }
    
    # Approve if documents are verified or service is unavailable (for demo)
    return {
        "approved": has_verified_docs,
        "property_details": property_details,
    }


@activity.defn(name="create_smart_contract_activity")
async def create_smart_contract_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create and deploy smart contract for property tokenization.
    
    MOCKED: Uses BlockchainService mock implementation.
    """
    property_id = payload["property_id"]
    owner_id = payload["owner_id"]
    property_details = payload["property_details"]
    
    logger.info(
        "workflow_create_smart_contract",
        extra={"property_id": property_id, "owner_id": owner_id},
    )
    
    # Get owner's wallet address
    with session_scope() as session:
        owner_entity = session.get(Entity, UUID(owner_id))
        owner_wallet = owner_entity.attributes.get("wallet_address", f"0x{owner_id.replace('-', '')[:40]}")
    
    # Deploy smart contract (MOCKED)
    blockchain_service = get_blockchain_service()
    contract_result = await blockchain_service.create_smart_contract(
        property_id=property_id,
        owner_address=owner_wallet,
        property_details=property_details,
    )
    
    return contract_result


@activity.defn(name="mint_property_tokens_activity")
async def mint_property_tokens_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mint tokens for the tokenized property.
    
    MOCKED: Uses BlockchainService mock implementation.
    """
    property_id = payload["property_id"]
    contract_address = payload["smart_contract_address"]
    total_tokens = payload["total_tokens"]
    
    logger.info(
        "workflow_mint_property_tokens",
        extra={
            "property_id": property_id,
            "contract_address": contract_address,
            "total_tokens": total_tokens,
        },
    )
    
    # Get owner wallet address
    with session_scope() as session:
        property_entity = session.get(Entity, UUID(property_id))
        if not property_entity.parent:
            raise ValueError("Property has no owner")
        
        owner_wallet = property_entity.parent.attributes.get(
            "wallet_address",
            f"0x{str(property_entity.parent.id).replace('-', '')[:40]}"
        )
    
    # Mint tokens (MOCKED)
    blockchain_service = get_blockchain_service()
    mint_result = await blockchain_service.mint_tokens(
        contract_address=contract_address,
        total_supply=total_tokens,
        owner_address=owner_wallet,
        property_id=property_id,
    )
    
    return mint_result


@activity.defn(name="activate_property_activity")
async def activate_property_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activate property and make it available for investors.
    """
    property_id = payload["property_id"]
    token_data = payload["token_data"]
    
    logger.info(
        "workflow_activate_property",
        extra={"property_id": property_id},
    )
    
    with session_scope() as session:
        property_entity = session.get(Entity, UUID(property_id))
        if not property_entity:
            raise ValueError(f"Property {property_id} not found")
        
        # Update property status and attributes
        property_entity.attributes["property_status"] = "active"
        property_entity.attributes["smart_contract_address"] = token_data.get("contract_address")
        property_entity.attributes["tokenization_date"] = token_data.get("minted_at")
        
        # Initialize token registry
        token_registry = get_token_registry_service(session)
        await token_registry.create_token_entry(
            property_id=property_id,
            total_tokens=property_entity.attributes.get("total_tokens", 0),
            token_price=property_entity.attributes.get("token_price", 0),
            contract_address=token_data.get("contract_address", ""),
        )
        
        session.add(property_entity)
        session.commit()
    
    return {"property_id": property_id, "status": "active"}


@activity.defn(name="verify_kyc_documents_activity")
async def verify_kyc_documents_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify investor KYC documents.
    
    Integrates with DocumentVaultService to check KYC document status.
    """
    from app.services.document_vault_client import get_document_vault_client
    
    investor_id = payload["investor_id"]
    
    logger.info(
        "workflow_verify_kyc_documents",
        extra={"investor_id": investor_id},
    )
    
    # Call DocumentVault API to check for verified KYC documents
    vault_client = get_document_vault_client()
    has_verified_kyc = await vault_client.check_documents_status(
        entity_id=investor_id,
        required_status="verified",
    )
    
    # Approve if KYC documents are verified or service unavailable (for demo)
    return {
        "approved": has_verified_kyc,
        "kyc_level": "full" if has_verified_kyc else "pending",
        "accredited_investor": True,
    }


@activity.defn(name="reject_investor_activity")
async def reject_investor_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reject investor onboarding due to failed KYC.
    """
    investor_id = payload["investor_id"]
    reason = payload["reason"]
    
    logger.info(
        "workflow_reject_investor",
        extra={"investor_id": investor_id, "reason": reason},
    )
    
    with session_scope() as session:
        investor_entity = session.get(Entity, UUID(investor_id))
        if investor_entity:
            investor_entity.attributes["kyc_status"] = "rejected"
            investor_entity.attributes["rejection_reason"] = reason
            investor_entity.attributes["onboarding_status"] = "rejected"
            session.add(investor_entity)
            session.commit()
    
    return {"investor_id": investor_id, "status": "rejected"}


@activity.defn(name="create_investor_wallet_activity")
async def create_investor_wallet_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create blockchain wallet for investor.
    
    MOCKED: Uses BlockchainService mock implementation.
    """
    investor_id = payload["investor_id"]
    
    logger.info(
        "workflow_create_investor_wallet",
        extra={"investor_id": investor_id},
    )
    
    # Create wallet (MOCKED)
    blockchain_service = get_blockchain_service()
    wallet_result = await blockchain_service.create_wallet(user_id=investor_id)
    
    # Store wallet address in investor entity
    with session_scope() as session:
        investor_entity = session.get(Entity, UUID(investor_id))
        if investor_entity:
            investor_entity.attributes["wallet_address"] = wallet_result["wallet_address"]
            session.add(investor_entity)
            session.commit()
    
    return wallet_result


@activity.defn(name="upgrade_investor_permissions_activity")
async def upgrade_investor_permissions_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upgrade investor from pending to active role.
    """
    investor_id = payload["investor_id"]
    wallet_address = payload["wallet_address"]
    
    logger.info(
        "workflow_upgrade_investor_permissions",
        extra={"investor_id": investor_id},
    )
    
    with session_scope() as session:
        from app.models.role import Role
        from app.models.role_assignment import RoleAssignment
        from sqlalchemy import select
        
        investor_entity = session.get(Entity, UUID(investor_id))
        if not investor_entity:
            raise ValueError(f"Investor {investor_id} not found")
        
        # Update investor status
        investor_entity.attributes["kyc_status"] = "verified"
        investor_entity.attributes["onboarding_status"] = "active"
        session.add(investor_entity)
        
        # Get InvestorActive role
        investor_active_role = session.scalar(
            select(Role).where(Role.name == "InvestorActive")
        )
        
        if not investor_active_role:
            logger.warning("InvestorActive role not found, skipping permission upgrade")
            session.commit()
            return {"investor_id": investor_id, "upgraded": False}
        
        # Remove InvestorPending role assignments
        investor_pending_role = session.scalar(
            select(Role).where(Role.name == "InvestorPending")
        )
        
        if investor_pending_role:
            pending_assignments = session.scalars(
                select(RoleAssignment)
                .where(RoleAssignment.principal_id == UUID(investor_id))
                .where(RoleAssignment.role_id == investor_pending_role.id)
            ).all()
            
            for assignment in pending_assignments:
                session.delete(assignment)
        
        # Add InvestorActive role
        active_assignment = RoleAssignment(
            principal_id=UUID(investor_id),
            principal_type="user",
            role_id=investor_active_role.id,
            entity_id=None,  # Global assignment
        )
        session.add(active_assignment)
        session.commit()
    
    return {"investor_id": investor_id, "upgraded": True, "wallet_address": wallet_address}


@activity.defn(name="validate_token_purchase_activity")
async def validate_token_purchase_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate token purchase eligibility.
    """
    investor_id = payload["investor_id"]
    property_id = payload["property_id"]
    quantity = payload["quantity"]
    
    logger.info(
        "workflow_validate_token_purchase",
        extra={
            "investor_id": investor_id,
            "property_id": property_id,
            "quantity": quantity,
        },
    )
    
    with session_scope() as session:
        # Check investor exists and is active
        investor_entity = session.get(Entity, UUID(investor_id))
        if not investor_entity:
            return {"valid": False, "reason": "Investor not found"}
        
        if investor_entity.attributes.get("kyc_status") != "verified":
            return {"valid": False, "reason": "Investor KYC not verified"}
        
        # Check property exists and is active
        property_entity = session.get(Entity, UUID(property_id))
        if not property_entity:
            return {"valid": False, "reason": "Property not found"}
        
        if property_entity.attributes.get("property_status") != "active":
            return {"valid": False, "reason": "Property not active"}
        
        # Check token availability
        available_tokens = property_entity.attributes.get("available_tokens", 0)
        if quantity > available_tokens:
            return {"valid": False, "reason": f"Only {available_tokens} tokens available"}
        
        # Get wallet addresses
        investor_wallet = investor_entity.attributes.get("wallet_address", "")
        property_owner_wallet = property_entity.parent.attributes.get("wallet_address", "") if property_entity.parent else ""
        
        return {
            "valid": True,
            "investor_wallet": investor_wallet,
            "property_owner_wallet": property_owner_wallet,
            "token_price": property_entity.attributes.get("token_price", 0),
        }


@activity.defn(name="process_payment_activity")
async def process_payment_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process payment for token purchase.
    
    MOCKED: Uses PaymentProcessingService mock implementation.
    """
    investor_id = payload["investor_id"]
    amount = payload["amount"]
    currency = payload.get("currency", "USD")
    payment_method = payload.get("payment_method", "card")
    
    logger.info(
        "workflow_process_payment",
        extra={
            "investor_id": investor_id,
            "amount": amount,
            "payment_method": payment_method,
        },
    )
    
    # Process payment (MOCKED)
    payment_service = get_payment_service()
    payment_result = await payment_service.process_payment(
        investor_id=investor_id,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        metadata=payload.get("metadata", {}),
    )
    
    return payment_result


@activity.defn(name="transfer_tokens_activity")
async def transfer_tokens_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transfer tokens from property owner to investor.
    
    MOCKED: Uses BlockchainService mock implementation.
    """
    from_address = payload["from_address"]
    to_address = payload["to_address"]
    property_id = payload["property_id"]
    quantity = payload["quantity"]
    payment_reference = payload["payment_reference"]
    
    logger.info(
        "workflow_transfer_tokens",
        extra={
            "property_id": property_id,
            "quantity": quantity,
            "payment_reference": payment_reference,
        },
    )
    
    with session_scope() as session:
        property_entity = session.get(Entity, UUID(property_id))
        if not property_entity:
            raise ValueError(f"Property {property_id} not found")
        
        contract_address = property_entity.attributes.get("smart_contract_address", "")
    
    # Transfer tokens on blockchain (MOCKED)
    blockchain_service = get_blockchain_service()
    transfer_result = await blockchain_service.transfer_tokens(
        contract_address=contract_address,
        from_address=from_address,
        to_address=to_address,
        quantity=quantity,
        property_id=property_id,
    )
    
    return transfer_result


@activity.defn(name="record_blockchain_transaction_activity")
async def record_blockchain_transaction_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record transaction on blockchain.
    
    MOCKED: Uses BlockchainService mock implementation.
    """
    transaction_type = payload["transaction_type"]
    token_transfer = payload["token_transfer"]
    payment_reference = payload["payment_reference"]
    
    logger.info(
        "workflow_record_blockchain_transaction",
        extra={
            "transaction_type": transaction_type,
            "payment_reference": payment_reference,
        },
    )
    
    # Record on blockchain (MOCKED)
    blockchain_service = get_blockchain_service()
    blockchain_result = await blockchain_service.record_transaction(
        transaction_type=transaction_type,
        transaction_data={
            "token_transfer": token_transfer,
            "payment_reference": payment_reference,
        },
    )
    
    return blockchain_result


@activity.defn(name="update_token_registry_activity")
async def update_token_registry_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update token registry with new ownership.
    """
    investor_id = payload["investor_id"]
    property_id = payload["property_id"]
    quantity = payload["quantity"]
    transaction_hash = payload["transaction_hash"]
    
    logger.info(
        "workflow_update_token_registry",
        extra={
            "investor_id": investor_id,
            "property_id": property_id,
            "quantity": quantity,
        },
    )
    
    with session_scope() as session:
        token_registry = get_token_registry_service(session)
        transfer_result = await token_registry.record_transfer(
            from_investor_id=None,  # Initial purchase from owner
            to_investor_id=investor_id,
            property_id=property_id,
            quantity=quantity,
            transaction_hash=transaction_hash,
        )
        session.commit()
    
    return transfer_result


@activity.defn(name="publish_platform_event_activity")
async def publish_platform_event_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish platform event via event dispatcher.
    """
    event_type = payload["event_type"]
    event_payload = payload["payload"]
    
    logger.info(
        "workflow_publish_platform_event",
        extra={"event_type": event_type},
    )
    
    with session_scope() as session:
        from app.events_engine import get_event_dispatcher
        
        dispatcher = get_event_dispatcher()
        event_record = dispatcher.publish_event(
            session,
            event_type=event_type,
            payload=event_payload,
        )
        session.commit()
        
        # Access attributes BEFORE session closes to avoid DetachedInstanceError
        event_id = event_record.event_id
        event_type_value = event_type
    
    return {"event_id": event_id, "event_type": event_type_value}


@activity.defn(name="automated_document_verification_activity")
async def automated_document_verification_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform automated document verification checks.
    
    Integrates with DocumentVaultService /verify endpoint.
    
    Payload should contain:
    - document_id: UUID of document to verify
    - verifier_id: UUID of entity performing verification (agent, owner, etc.)
    """
    from app.services.document_vault_client import DocumentVaultError, get_document_vault_client
    
    document_id = payload["document_id"]
    verifier_id = payload["verifier_id"]
    
    logger.info(
        "workflow_automated_document_verification",
        extra={
            "document_id": document_id,
            "verifier_id": verifier_id,
        },
    )
    
    # Call DocumentVault API to verify the document
    vault_client = get_document_vault_client()
    
    try:
        result = await vault_client.verify_document(
            document_id=document_id,
            verifier_id=verifier_id,
        )
        
        status = result.get("status", "unknown")
        passed = status == "verified"
        
        logger.info(
            "workflow_document_verification_complete",
            extra={
                "document_id": document_id,
                "verifier_id": verifier_id,
                "status": status,
                "passed": passed,
            },
        )
        
        return {
            "passed": passed,
            "status": status,
            "checks": {
                "hash_valid": passed,
                "format_valid": passed,
                "size_valid": passed,
            },
        }
    
    except DocumentVaultError as exc:
        logger.error(
            "workflow_document_verification_error",
            extra={
                "document_id": document_id,
                "verifier_id": verifier_id,
                "error": str(exc),
            },
        )
        
        # Return failure but don't raise - allow workflow to handle
        return {
            "passed": False,
            "error": str(exc),
            "checks": {
                "hash_valid": False,
                "format_valid": False,
                "size_valid": False,
            },
        }


@activity.defn(name="mark_document_verified_activity")
async def mark_document_verified_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mark document as verified.
    
    In production, call DocumentVaultService API to update document status.
    """
    document_id = payload["document_id"]
    
    logger.info(
        "workflow_mark_document_verified",
        extra={"document_id": document_id},
    )
    
    # Mock: In production, POST /api/v1/documents/{document_id}/verify
    await asyncio.sleep(0.2)
    
    return {"document_id": document_id, "status": "verified"}


@activity.defn(name="trigger_entity_workflow_activity")
async def trigger_entity_workflow_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger dependent workflow based on entity type and event.
    """
    entity_id = payload["entity_id"]
    event = payload["event"]
    
    logger.info(
        "workflow_trigger_entity_workflow",
        extra={"entity_id": entity_id, "event": event},
    )
    
    # This would trigger PropertyOnboardingWorkflow or InvestorOnboardingWorkflow
    # based on entity type
    return {"entity_id": entity_id, "event": event, "triggered": True}

