# Quick Start Guide - Real Estate Tokenization Demo

## 📋 Overview

This guide provides the essential steps to set up and demonstrate the real estate tokenization platform.

---

## 🎯 Demo Scenarios

1. **Agent** onboards property owner and creates property listing
2. **Property Owner** uploads documents → Property tokenized → Goes live
3. **Agent** onboards investor → Investor uploads KYC → Gets approved
4. **Investor** browses properties → Purchases tokens

---

## 🚀 Prerequisites

### Services Required:
- [x] Entity & Permissions Core (EPR) - `http://localhost:8000`
- [x] DocumentVault Service - `http://localhost:8001`
- [x] Temporal Server - `localhost:7233`
- [x] PostgreSQL Database
- [x] Redis Cache

### Start Services:
```bash
# Terminal 1: Start EPR API
make run
# Or: uvicorn app.main:app --reload --port 8000

# Terminal 2: Start Temporal Worker
make worker
# Or: python -m app.workers.temporal_worker

# Terminal 3: Start DocumentVault (separate service)
# Follow DocumentVault startup instructions
```

---

## 📝 Implementation Checklist

### ✅ Phase 1: Setup (Will be developed)
- [ ] Create new permissions (property:*, token:*, user:*)
- [ ] Create 4 roles (Agent, PropertyOwner, InvestorPending, InvestorActive)
- [ ] Create seed data script
- [ ] Add mocked service classes

### ✅ Phase 2: Workflows (Will be developed)
- [ ] PropertyOnboardingWorkflow
- [ ] InvestorOnboardingWorkflow
- [ ] TokenPurchaseWorkflow
- [ ] DocumentVerificationWorkflow

### ✅ Phase 3: API Endpoints (Will be developed)
- [ ] Property management endpoints
- [ ] Token operations endpoints
- [ ] User onboarding endpoints
- [ ] Workflow trigger endpoints

### ✅ Phase 4: Mocked Services
- [ ] BlockchainService (mock)
- [ ] TokenRegistryService (mock)
- [ ] PaymentProcessingService (mock)

---

## 🔧 Initial Setup Commands

### Step 1: Initialize Demo Data
```bash
# This will create all permissions, roles, and a demo agent
curl -X POST http://localhost:8000/api/v1/setup/initialize-demo \
  -H "Content-Type: application/json"

# Response includes:
# - agent_id
# - role_ids (map of role names to IDs)
# - permission_ids
```

**Save these IDs for subsequent calls!**

---

## 📊 Demo Execution Flow

### Scenario 1: Property Owner Onboarding

**Step 1.1: Agent creates property owner**
```bash
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: <AGENT_ID>" \
  -d '{
    "name": "ABC Properties LLC",
    "type": "issuer",
    "attributes": {
      "company_name": "ABC Properties LLC",
      "contact_email": "owner@abc.com"
    }
  }'
```

**Step 1.2: Assign PropertyOwner role**
```bash
curl -X POST http://localhost:8000/api/v1/assignments \
  -d '{
    "principal_id": "<OWNER_ID>",
    "principal_type": "user",
    "role_id": "<PROPERTY_OWNER_ROLE_ID>",
    "entity_id": "<OWNER_ID>"
  }'
```

### Scenario 2: Property Creation & Tokenization

**Step 2.1: Create property**
```bash
curl -X POST http://localhost:8000/api/v1/entities \
  -H "X-Actor-Id: <OWNER_ID>" \
  -d '{
    "name": "Sunset Apartments",
    "type": "offering",
    "parent_id": "<OWNER_ID>",
    "attributes": {
      "property_type": "residential",
      "address": "123 Sunset Blvd, LA, CA",
      "valuation": 5000000,
      "total_tokens": 50000,
      "token_price": 100
    }
  }'
```

**Step 2.2: Upload property documents**
```bash
# Upload to DocumentVault
# - Operating agreement
# - Title deed
# - Appraisal report
```

**Step 2.3: Trigger property onboarding workflow**
```bash
curl -X POST http://localhost:8000/api/v1/workflows/property-onboarding \
  -d '{
    "property_id": "<PROPERTY_ID>",
    "owner_id": "<OWNER_ID>"
  }'
```

**What happens in the workflow:**
1. ✅ Verifies documents
2. ✅ Creates smart contract (mocked)
3. ✅ Mints tokens (mocked)
4. ✅ Updates property status to "active"
5. ✅ Publishes "property.activated" event

### Scenario 3: Investor Onboarding

**Step 3.1: Agent creates investor**
```bash
curl -X POST http://localhost:8000/api/v1/entities \
  -H "X-Actor-Id: <AGENT_ID>" \
  -d '{
    "name": "John Doe",
    "type": "investor",
    "attributes": {
      "email": "john@investor.com",
      "investor_type": "individual"
    }
  }'
```

**Step 3.2: Assign InvestorPending role**
```bash
curl -X POST http://localhost:8000/api/v1/assignments \
  -d '{
    "principal_id": "<INVESTOR_ID>",
    "role_id": "<INVESTOR_PENDING_ROLE_ID>"
  }'
```

**Step 3.3: Upload KYC documents**
```bash
# Upload to DocumentVault
# - ID proof
# - Address proof
# - Income verification
```

**Step 3.4: Trigger investor onboarding workflow**
```bash
curl -X POST http://localhost:8000/api/v1/workflows/investor-onboarding \
  -d '{
    "investor_id": "<INVESTOR_ID>"
  }'
```

**What happens in the workflow:**
1. ✅ Verifies KYC documents
2. ✅ Creates blockchain wallet (mocked)
3. ✅ Upgrades role from InvestorPending → InvestorActive
4. ✅ Publishes "investor.activated" event

### Scenario 4: Token Purchase

**Step 4.1: Investor views available properties**
```bash
curl -X GET "http://localhost:8000/api/v1/properties?status=active"
```

**Step 4.2: Get token details**
```bash
curl -X GET "http://localhost:8000/api/v1/tokens/<PROPERTY_ID>"
```

**Step 4.3: Purchase tokens**
```bash
curl -X POST http://localhost:8000/api/v1/tokens/purchase \
  -H "X-Actor-Id: <INVESTOR_ID>" \
  -d '{
    "investor_id": "<INVESTOR_ID>",
    "property_id": "<PROPERTY_ID>",
    "token_quantity": 10,
    "payment_amount": 1000
  }'
```

**What happens in the workflow:**
1. ✅ Validates purchase eligibility
2. ✅ Processes payment (mocked - always succeeds)
3. ✅ Transfers tokens (mocked blockchain call)
4. ✅ Records blockchain transaction (mocked)
5. ✅ Updates token registry
6. ✅ Publishes "token.purchased" event

**Step 4.4: View holdings**
```bash
curl -X GET "http://localhost:8000/api/v1/tokens/holdings?investor_id=<INVESTOR_ID>"
```

---

## 🔍 Monitoring & Debugging

### Check Workflow Status
```bash
# Using Temporal CLI
temporal workflow describe --workflow-id <WORKFLOW_ID>

# Or via API
curl -X GET "http://localhost:8000/api/v1/workflows/<WORKFLOW_ID>/status"
```

### View Events
```bash
curl -X GET "http://localhost:8000/api/v1/events?event_type=property.activated"
```

### Check Audit Logs
```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?entity_id=<ENTITY_ID>"
```

---

## 🎨 Frontend Dashboard (Next Phase)

The dashboard will have these views:

### Agent Dashboard
- **Property Owners Tab**
  - List owners
  - Onboard new owner
  - View owner properties
  
- **Investors Tab**
  - List investors
  - Onboard new investor
  - Approve pending investors
  
- **Properties Tab**
  - List all properties
  - View property details
  - Approve properties

### Investor Portal
- **Browse Properties**
  - Filter by type, location, price
  - View property details
  - See tokenomics (total tokens, price, available)
  
- **My Holdings**
  - View owned tokens
  - Portfolio valuation
  - Transaction history
  
- **Trade**
  - Purchase tokens
  - (Future) Sell tokens on secondary market

---

## 📚 Key Concepts

### Entity Hierarchy
```
Agent (type: agent)
└─ Property Owner (type: issuer)
   └─ Property (type: offering)

Investor (type: investor)
```

### Permission Flow
```
InvestorPending Role:
- property:view ✅
- token:view ✅
- token:trade ❌

InvestorActive Role:
- property:view ✅
- token:view ✅
- token:trade ✅  (Upgraded after KYC approval)
```

### Workflow Triggers
```
Document Upload → DocumentVerificationWorkflow
  ↓
Property Documents Verified → PropertyOnboardingWorkflow
  ↓
Property Activated → Listed for investors

KYC Documents Verified → InvestorOnboardingWorkflow
  ↓
Investor Activated → Can trade tokens

Token Purchase Request → TokenPurchaseWorkflow
  ↓
Token Transfer Complete → Investor owns tokens
```

---

## ⚠️ Mocked Components

These components return successful responses without real implementation:

1. **BlockchainService**
   - `create_smart_contract()` - Returns fake contract address
   - `mint_tokens()` - Returns fake transaction hash
   - `transfer_tokens()` - Returns fake transaction hash

2. **TokenRegistryService**
   - `create_token_entry()` - Stores in-memory
   - `record_transfer()` - Updates in-memory balances

3. **PaymentProcessingService**
   - `process_payment()` - Always returns success
   - Payment is NOT actually charged

4. **Smart Contract Signing**
   - Simulated with activity delay
   - No actual signature verification

---

## 🚀 Next Steps

1. **Review** this implementation plan
2. **Confirm** the approach and scenarios
3. **Implement** the backend workflows
4. **Test** end-to-end demo scenarios
5. **Document** API specifications
6. **Build** frontend dashboard (next phase)

---

## 📞 Need Help?

Check these files for detailed specifications:
- `docs/TOKENIZATION_IMPLEMENTATION_PLAN.md` - Complete technical plan
- `docs/ARCHITECTURE.md` - System architecture
- `README.md` - Service overview

---

**Estimated Timeline:**
- Backend Development: 5-7 days
- Testing & Refinement: 2-3 days
- **Total: ~2 weeks for demo-ready backend**


