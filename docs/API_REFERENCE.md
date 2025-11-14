## Real Estate Tokenization Platform - API Reference

### Base URL
```
http://localhost:8000 (local development)
https://your-domain.com (production)
```

### Authentication
All mutating endpoints accept an optional `X-Actor-Id` header for audit tracking:
```
X-Actor-Id: <uuid>
```

---

## Setup & Initialization

### Initialize Demo Environment
**POST** `/api/v1/setup/initialize-demo`

Creates all required permissions, roles, and a demo agent for testing.

**Response:**
```json
{
  "permissions_created": 13,
  "roles_created": 4,
  "agent_created": true,
  "agent_id": "uuid",
  "role_ids": {
    "Agent": "uuid",
    "PropertyOwner": "uuid",
    "InvestorPending": "uuid",
    "InvestorActive": "uuid"
  },
  "permission_ids": {...},
  "message": "Demo environment initialized successfully",
  "next_steps": [...]
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/setup/initialize-demo
```

### Create Sample Data
**POST** `/api/v1/setup/create-sample-data`

Creates 2 property owners, 3 investors, and 3 properties for demo purposes.

**Response:**
```json
{
  "owners_created": 2,
  "investors_created": 3,
  "properties_created": 3,
  "owner_ids": ["uuid1", "uuid2"],
  "investor_ids": ["uuid1", "uuid2", "uuid3"],
  "property_ids": ["uuid1", "uuid2", "uuid3"]
}
```

---

## User Onboarding

### Onboard Property Owner
**POST** `/api/v1/onboarding/property-owner`

Creates an issuer entity and assigns PropertyOwner role.

**Request Body:**
```json
{
  "name": "Luxury Real Estate LLC",
  "company_name": "Luxury Real Estate LLC",
  "contact_email": "owner@luxuryrealestate.com",
  "phone": "+1234567890",
  "address": "123 Business Ave",
  "attributes": {}
}
```

**Response:**
```json
{
  "entity_id": "uuid",
  "name": "Luxury Real Estate LLC",
  "entity_type": "issuer",
  "role_assigned": true,
  "role_id": "uuid",
  "onboarding_status": "completed",
  "message": "Property owner onboarded successfully"
}
```

### Onboard Investor
**POST** `/api/v1/onboarding/investor`

Creates an investor entity with InvestorPending role.

**Request Body:**
```json
{
  "name": "John Investor",
  "email": "john@investor.com",
  "phone": "+1234567890",
  "investor_type": "individual",
  "attributes": {}
}
```

**Response:**
```json
{
  "entity_id": "uuid",
  "name": "John Investor",
  "entity_type": "investor",
  "role_assigned": true,
  "role_id": "uuid",
  "onboarding_status": "pending",
  "message": "Investor onboarded. Complete KYC verification to activate."
}
```

### Activate Investor
**POST** `/api/v1/onboarding/investor/{investor_id}/activate`

Starts InvestorOnboardingWorkflow to verify KYC and activate investor.

**Response:**
```json
{
  "workflow_id": "investor-onboarding-uuid",
  "investor_id": "uuid",
  "status": "started",
  "message": "Investor activation workflow started successfully"
}
```

---

## Property Management

### Create Property
**POST** `/api/v1/properties`

Creates a new property listing in pending status.

**Request Body:**
```json
{
  "name": "Sunset Boulevard Apartments",
  "owner_id": "owner-uuid",
  "property_type": "residential",
  "address": "123 Sunset Blvd, Los Angeles, CA 90028",
  "valuation": 5000000,
  "total_tokens": 50000,
  "token_price": 100,
  "minimum_investment": 1000,
  "description": "Luxury apartments...",
  "attributes": {}
}
```

**Response:**
```json
{
  "id": "property-uuid",
  "name": "Sunset Boulevard Apartments",
  "owner_id": "owner-uuid",
  "property_type": "residential",
  "address": "123 Sunset Blvd, Los Angeles, CA 90028",
  "valuation": 5000000,
  "total_tokens": 50000,
  "token_price": 100,
  "available_tokens": 50000,
  "property_status": "pending",
  "smart_contract_address": null,
  "tokenization_date": null,
  "minimum_investment": 1000,
  "description": "Luxury apartments...",
  "created_at": "2025-11-12T...",
  "updated_at": "2025-11-12T..."
}
```

### Get Property
**GET** `/api/v1/properties/{property_id}`

Retrieves property details.

### List Properties
**GET** `/api/v1/properties`

Lists properties with optional filters.

**Query Parameters:**
- `status` (optional): pending, active, sold_out
- `property_type` (optional): residential, commercial, industrial
- `owner_id` (optional): Filter by owner UUID
- `page` (default: 1): Page number
- `page_size` (default: 50, max: 100): Results per page

**Response:**
```json
{
  "properties": [...],
  "total": 10,
  "page": 1,
  "page_size": 50
}
```

### Update Property
**PATCH** `/api/v1/properties/{property_id}`

Updates property details.

**Request Body:**
```json
{
  "name": "Updated Name",
  "valuation": 5500000,
  "token_price": 110
}
```

### Tokenize Property
**POST** `/api/v1/properties/tokenize`

Initiates PropertyOnboardingWorkflow to tokenize property.

**Request Body:**
```json
{
  "property_id": "property-uuid",
  "owner_id": "owner-uuid"
}
```

**Response:**
```json
{
  "property_id": "property-uuid",
  "workflow_id": "property-onboarding-uuid",
  "status": "started",
  "message": "Property tokenization workflow started successfully"
}
```

**Workflow Steps:**
1. Verifies property documents
2. Creates smart contract (mocked)
3. Mints tokens (mocked)
4. Updates property status to "active"
5. Publishes "property.activated" event

---

## Token Operations

### Get Token Details
**GET** `/api/v1/tokens/{property_id}`

Retrieves token information for a property.

**Response:**
```json
{
  "property_id": "uuid",
  "property_name": "Sunset Boulevard Apartments",
  "total_tokens": 50000,
  "token_price": 100.0,
  "available_tokens": 45000,
  "smart_contract_address": "0x...",
  "property_type": "residential",
  "address": "123 Sunset Blvd...",
  "valuation": 5000000
}
```

### Purchase Tokens
**POST** `/api/v1/tokens/purchase`

Initiates TokenPurchaseWorkflow to buy property tokens.

**Request Body:**
```json
{
  "investor_id": "investor-uuid",
  "property_id": "property-uuid",
  "token_quantity": 100,
  "payment_method": "card"
}
```

**Response:**
```json
{
  "workflow_id": "token-purchase-uuid",
  "investor_id": "investor-uuid",
  "property_id": "property-uuid",
  "token_quantity": 100,
  "payment_amount": 10000.0,
  "status": "started",
  "message": "Token purchase workflow started successfully"
}
```

**Workflow Steps:**
1. Validates purchase eligibility
2. Processes payment (mocked)
3. Transfers tokens on blockchain (mocked)
4. Records transaction (mocked)
5. Updates token registry
6. Publishes "token.purchased" event

### Get Investor Holdings
**GET** `/api/v1/tokens/holdings/{investor_id}`

Retrieves investor's token portfolio.

**Response:**
```json
{
  "investor_id": "uuid",
  "holdings": [
    {
      "property_id": "uuid",
      "property_name": "Sunset Apartments",
      "quantity": 100,
      "token_price": 100.0,
      "value": 10000.0
    }
  ],
  "total_value": 10000.0,
  "properties_count": 1
}
```

### Get Available Tokens
**GET** `/api/v1/tokens/available/{property_id}`

Returns number of tokens available for purchase.

**Response:**
```json
{
  "property_id": "uuid",
  "available_tokens": 45000
}
```

---

## Complete Demo Workflow

### 1. Initial Setup
```bash
# Initialize demo environment
curl -X POST http://localhost:8000/api/v1/setup/initialize-demo

# Save the agent_id from response
AGENT_ID="<agent-uuid>"
```

### 2. Onboard Property Owner
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/property-owner \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: $AGENT_ID" \
  -d '{
    "name": "ABC Properties LLC",
    "company_name": "ABC Properties LLC",
    "contact_email": "owner@abc.com"
  }'

# Save owner_id
OWNER_ID="<owner-uuid>"
```

### 3. Create Property
```bash
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: $OWNER_ID" \
  -d '{
    "name": "Luxury Condos",
    "owner_id": "'$OWNER_ID'",
    "property_type": "residential",
    "address": "123 Main St",
    "valuation": 5000000,
    "total_tokens": 50000,
    "token_price": 100
  }'

# Save property_id
PROPERTY_ID="<property-uuid>"
```

### 4. Tokenize Property
```bash
curl -X POST http://localhost:8000/api/v1/properties/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "'$PROPERTY_ID'",
    "owner_id": "'$OWNER_ID'"
  }'
```

### 5. Onboard Investor
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/investor \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: $AGENT_ID" \
  -d '{
    "name": "John Investor",
    "email": "john@investor.com",
    "investor_type": "individual"
  }'

# Save investor_id
INVESTOR_ID="<investor-uuid>"
```

### 6. Activate Investor
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/investor/$INVESTOR_ID/activate \
  -H "X-Actor-Id: $AGENT_ID"
```

### 7. Purchase Tokens
```bash
curl -X POST http://localhost:8000/api/v1/tokens/purchase \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: $INVESTOR_ID" \
  -d '{
    "investor_id": "'$INVESTOR_ID'",
    "property_id": "'$PROPERTY_ID'",
    "token_quantity": 100,
    "payment_method": "card"
  }'
```

### 8. View Holdings
```bash
curl http://localhost:8000/api/v1/tokens/holdings/$INVESTOR_ID
```

---

## Temporal Workflows

### Starting the Temporal Worker

**Local Development:**
```bash
# Export Temporal Cloud credentials
export EPR_TEMPORAL_HOST="your-namespace.tmprl.cloud:7233"
export EPR_TEMPORAL_NAMESPACE="your-namespace"
export EPR_TEMPORAL_API_KEY="your-api-key"
export EPR_TEMPORAL_TASK_QUEUE="omen-workflows"
export EPR_TEMPORAL_TLS_ENABLED="true"

# Start worker
python -m app.workflow_orchestration.worker
```

### Available Workflows

1. **PropertyOnboardingWorkflow**
   - Triggered by: POST /api/v1/properties/tokenize
   - Duration: Minutes
   - Steps: Document verification → Smart contract → Token minting → Activation

2. **InvestorOnboardingWorkflow**
   - Triggered by: POST /api/v1/onboarding/investor/{id}/activate
   - Duration: Minutes to hours
   - Steps: KYC verification → Wallet creation → Permission upgrade

3. **TokenPurchaseWorkflow**
   - Triggered by: POST /api/v1/tokens/purchase
   - Duration: Seconds to minutes
   - Steps: Validation → Payment → Token transfer → Blockchain recording

4. **DocumentVerificationWorkflow**
   - Triggered by: Document upload events
   - Duration: Minutes to days
   - Steps: Automated verification → Manual approval → Status update

---

## Error Handling

### Common HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `202 Accepted`: Async operation started (workflows)
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `409 Conflict`: Duplicate resource
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Mocked Services

The following services return successful responses without real implementation:

### BlockchainService
- `create_smart_contract()` - Returns fake contract address
- `mint_tokens()` - Returns fake transaction hash
- `transfer_tokens()` - Returns fake transaction hash
- `create_wallet()` - Returns fake wallet address

### PaymentProcessingService
- `process_payment()` - Always returns success
- **Note:** No actual charges are made

### TokenRegistryService
- Token holdings stored in `entities.attributes` JSON field
- In-memory tracking for MVP demo

---

## Testing

### Run All Tests
```bash
pytest -vv
```

### Run Specific Test Modules
```bash
# Property tests
pytest tests/test_properties.py -vv

# Tokenization tests
pytest tests/test_tokenization.py -vv

# Mocked services tests
pytest tests/test_mocked_services.py -vv
```

---

## Next Steps for Production

1. **Blockchain Integration**
   - Deploy ERC-1400 smart contracts
   - Integrate Web3.py
   - Implement gas management

2. **Payment Processing**
   - Integrate Stripe/PayPal
   - Add Circle API for crypto payments
   - Implement PCI-DSS compliance

3. **Token Registry**
   - Create dedicated tables (see DATABASE_SCHEMA_CHANGES.md)
   - Implement real-time balance tracking
   - Add transfer history

4. **DocumentVault Integration**
   - Call /verify endpoint after document upload
   - Trigger workflows on verification completion

5. **Frontend Dashboard**
   - Agent dashboard for user management
   - Investor portal for trading
   - Property owner dashboard

---

## Support & Documentation

- **Implementation Plan**: `docs/TOKENIZATION_IMPLEMENTATION_PLAN.md`
- **Quick Start Guide**: `docs/QUICK_START_DEMO.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Deployment**: `docs/DEPLOYMENT.md`

For issues or questions, check the logs:
```bash
# API logs
tail -f logs/app.log

# Temporal worker logs
python -m app.workflow_orchestration.worker
```


