# Database Schema Changes for Tokenization Platform

## Analysis

After reviewing the existing schema, **NO new tables are required** for the MVP demo. We will leverage:

1. **Existing `entities` table** - Supports all entity types via the flexible `attributes` JSONB field
2. **Existing `roles` and `permissions` tables** - Will add new permission actions
3. **Existing `role_assignments` table** - No changes needed
4. **Existing `platform_events` table** - Already supports all event types

## ✅ No SQL Migration Required

All new data structures will use the existing schema:

### Entity Attributes Structure

**For Property (type: offering):**
```json
{
  "property_type": "residential",
  "address": "123 Main St",
  "valuation": 5000000,
  "total_tokens": 50000,
  "token_price": 100,
  "available_tokens": 50000,
  "property_status": "pending",
  "smart_contract_address": null,
  "token_holders": {}  // investor_id -> quantity
}
```

**For Property Owner (type: issuer):**
```json
{
  "company_name": "ABC Properties",
  "contact_email": "owner@abc.com",
  "onboarding_status": "completed",
  "kyc_status": "approved"
}
```

**For Investor (type: investor):**
```json
{
  "investor_type": "individual",
  "kyc_status": "pending",
  "wallet_address": null,
  "onboarding_status": "pending",
  "token_holdings": {}  // property_id -> quantity
}
```

## Future Schema (For Production)

When moving from MVP to production, consider these dedicated tables:

```sql
-- Token registry table
CREATE TABLE tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    token_symbol VARCHAR(10) NOT NULL,
    total_supply BIGINT NOT NULL,
    token_price DECIMAL(20, 2),
    contract_address VARCHAR(255),
    blockchain_network VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Token holdings table
CREATE TABLE token_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    property_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    quantity BIGINT NOT NULL CHECK (quantity >= 0),
    average_purchase_price DECIMAL(20, 2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(investor_id, property_id)
);

CREATE INDEX idx_token_holdings_investor ON token_holdings(investor_id);
CREATE INDEX idx_token_holdings_property ON token_holdings(property_id);

-- Transfer history table
CREATE TABLE token_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES entities(id),
    from_investor_id UUID REFERENCES entities(id),
    to_investor_id UUID REFERENCES entities(id),
    quantity BIGINT NOT NULL,
    price_per_token DECIMAL(20, 2),
    transaction_hash VARCHAR(255),
    transfer_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_token_transfers_property ON token_transfers(property_id);
CREATE INDEX idx_token_transfers_from ON token_transfers(from_investor_id);
CREATE INDEX idx_token_transfers_to ON token_transfers(to_investor_id);

-- Payment transactions table
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_id UUID REFERENCES entities(id),
    amount DECIMAL(20, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    payment_method VARCHAR(50),
    payment_provider VARCHAR(50),
    provider_transaction_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_payment_transactions_investor ON payment_transactions(investor_id);
CREATE INDEX idx_payment_transactions_status ON payment_transactions(status);
```

## Summary

✅ **For MVP Demo:** No database changes required - use existing schema  
📋 **For Production:** Add dedicated tables as shown above for better performance and data integrity


