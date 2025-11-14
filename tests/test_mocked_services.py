"""Tests for mocked services."""

from __future__ import annotations

import pytest

from app.services.blockchain import get_blockchain_service
from app.services.payment import get_payment_service


@pytest.mark.asyncio
async def test_blockchain_create_smart_contract() -> None:
    """Test blockchain smart contract creation (mocked)."""
    service = get_blockchain_service()
    
    result = await service.create_smart_contract(
        property_id="test-property-123",
        owner_address="0xowner123",
        property_details={"valuation": 1000000},
    )
    
    assert result["contract_address"].startswith("0x")
    assert result["transaction_hash"].startswith("0x")
    assert result["status"] == "deployed"


@pytest.mark.asyncio
async def test_blockchain_mint_tokens() -> None:
    """Test token minting (mocked)."""
    service = get_blockchain_service()
    
    result = await service.mint_tokens(
        contract_address="0xcontract123",
        total_supply=10000,
        owner_address="0xowner123",
        property_id="test-property-123",
    )
    
    assert result["transaction_hash"].startswith("0x")
    assert result["total_supply"] == 10000
    assert result["status"] == "confirmed"


@pytest.mark.asyncio
async def test_blockchain_transfer_tokens() -> None:
    """Test token transfer (mocked)."""
    service = get_blockchain_service()
    
    result = await service.transfer_tokens(
        contract_address="0xcontract123",
        from_address="0xfrom123",
        to_address="0xto123",
        quantity=100,
        property_id="test-property-123",
    )
    
    assert result["transaction_hash"].startswith("0x")
    assert result["quantity"] == 100
    assert result["status"] == "confirmed"


@pytest.mark.asyncio
async def test_blockchain_create_wallet() -> None:
    """Test wallet creation (mocked)."""
    service = get_blockchain_service()
    
    result = await service.create_wallet(user_id="test-user-123")
    
    assert result["wallet_address"].startswith("0x")
    assert result["user_id"] == "test-user-123"
    assert result["balance"] == "0"


@pytest.mark.asyncio
async def test_payment_process_payment() -> None:
    """Test payment processing (mocked)."""
    service = get_payment_service()
    
    result = await service.process_payment(
        investor_id="test-investor-123",
        amount=1000.00,
        currency="USD",
        payment_method="card",
    )
    
    assert result["success"] is True
    assert result["amount"] == 1000.00
    assert result["status"] == "completed"
    assert "transaction_id" in result


@pytest.mark.asyncio
async def test_payment_verify_payment() -> None:
    """Test payment verification (mocked)."""
    service = get_payment_service()
    
    result = await service.verify_payment(transaction_id="txn_123")
    
    assert result["status"] == "confirmed"
    assert result["transaction_id"] == "txn_123"


@pytest.mark.asyncio
async def test_payment_calculate_fees() -> None:
    """Test payment fee calculation (mocked)."""
    service = get_payment_service()
    
    result = await service.calculate_fees(amount=1000.00, payment_method="card")
    
    assert result["gross_amount"] == 1000.00
    assert result["fee_total"] > 0
    assert result["net_amount"] < result["gross_amount"]
    assert result["payment_method"] == "card"


@pytest.mark.asyncio
async def test_payment_initiate_refund() -> None:
    """Test payment refund (mocked)."""
    service = get_payment_service()
    
    result = await service.initiate_refund(
        transaction_id="txn_123",
        amount=500.00,
        reason="Token transfer failed",
    )
    
    assert result["success"] is True
    assert result["amount"] == 500.00
    assert result["status"] == "completed"
    assert "refund_id" in result



