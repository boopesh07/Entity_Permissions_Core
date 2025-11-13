# DocumentVault Service Integration

## Overview

The Entity Permissions & Roles (EPR) service now integrates with the DocumentVault microservice for document upload and verification operations. This integration replaces the previous mocked calls with actual HTTP API requests.

## Configuration

### Environment Variable

Add the following environment variable to your `.env` file:

```bash
DOCUMENT_VAULT_SERVICE_URL=https://your-document-vault-service.com
```

**Example for local development:**
```bash
DOCUMENT_VAULT_SERVICE_URL=http://localhost:8001
```

**Example for production:**
```bash
DOCUMENT_VAULT_SERVICE_URL=https://document-vault.omen.io
```

### Behavior When Not Configured

If `DOCUMENT_VAULT_SERVICE_URL` is not set or is empty:
- The system will **log warnings** indicating that DocumentVault operations are being mocked
- All document verification checks will **succeed automatically** (for demo purposes)
- Workflows will continue to function normally
- This allows for development and demo without requiring a running DocumentVault service

## Integration Points

### 1. Property Onboarding Workflow

**Activity:** `verify_property_documents_activity`

**API Call:**
- Checks for verified documents for a property entity
- Endpoint: `GET /api/v1/documents?entity_id={property_id}&status=verified`

**Behavior:**
- Returns `approved: true` if property has verified documents
- Returns `approved: false` if no verified documents found
- Auto-approves if DocumentVault service is unavailable

### 2. Investor Onboarding Workflow

**Activity:** `verify_kyc_documents_activity`

**API Call:**
- Checks for verified KYC documents for an investor entity
- Endpoint: `GET /api/v1/documents?entity_id={investor_id}&status=verified`

**Behavior:**
- Returns `approved: true` if investor has verified KYC documents
- Sets `kyc_level: "full"` on approval, `"pending"` otherwise
- Auto-approves if DocumentVault service is unavailable

### 3. Document Verification Workflow

**Activity:** `automated_document_verification_activity`

**API Call:**
- Triggers document verification process in DocumentVault
- Endpoint: `POST /api/v1/documents/verify`
- Request Body: `{"document_id": "uuid"}`

**Response:**
```json
{
  "document_id": "uuid",
  "status": "verified" | "mismatch" | "verification_failed",
  "verified_at": "2025-11-12T00:00:00Z"
}
```

**Behavior:**
- Returns `passed: true` if document status is "verified"
- Returns `passed: false` for any other status or on error
- Includes hash validation, format validation, and size validation checks

## DocumentVaultClient API

### Class: `DocumentVaultClient`

Located in `app/services/document_vault_client.py`

#### Methods

##### `verify_document(document_id: str) -> Dict[str, Any]`

Verifies a document via DocumentVault service.

**Parameters:**
- `document_id` (str): Document UUID to verify

**Returns:**
- Dictionary with verification results:
  ```python
  {
      "document_id": "uuid",
      "status": "verified",
      "verified_at": "timestamp"
  }
  ```

**Raises:**
- `DocumentVaultError`: If verification request fails

**Example:**
```python
from app.services.document_vault_client import get_document_vault_client

client = get_document_vault_client()
result = await client.verify_document("document-uuid")
print(result["status"])  # "verified"
```

##### `get_documents_by_entity(entity_id: str, status: Optional[str]) -> Dict[str, Any]`

Gets all documents for an entity.

**Parameters:**
- `entity_id` (str): Entity UUID
- `status` (str, optional): Filter by status (e.g., "verified", "uploaded")

**Returns:**
- Dictionary with document list:
  ```python
  {
      "documents": [...],
      "count": 5
  }
  ```

**Example:**
```python
result = await client.get_documents_by_entity(
    entity_id="property-uuid",
    status="verified"
)
print(f"Found {result['count']} verified documents")
```

##### `check_documents_status(entity_id: str, required_status: str) -> bool`

Checks if entity has documents with required status.

**Parameters:**
- `entity_id` (str): Entity UUID
- `required_status` (str): Required document status (default: "verified")

**Returns:**
- `True` if entity has documents with required status
- `False` otherwise
- `True` if service is unavailable (graceful degradation)

**Example:**
```python
has_verified = await client.check_documents_status(
    entity_id="investor-uuid",
    required_status="verified"
)
if has_verified:
    print("Investor has verified KYC documents")
```

### Singleton Pattern

The DocumentVaultClient uses a singleton pattern:

```python
from app.services.document_vault_client import get_document_vault_client

# Always returns the same instance
client = get_document_vault_client()
```

## Error Handling

### DocumentVaultError

All DocumentVault operations may raise `DocumentVaultError`:

```python
from app.services.document_vault_client import DocumentVaultError, get_document_vault_client

try:
    result = await client.verify_document(document_id)
except DocumentVaultError as exc:
    logger.error(f"Verification failed: {exc}")
    # Handle gracefully
```

### HTTP Errors

The client handles:
- **HTTP 4xx/5xx errors**: Raised as `DocumentVaultError`
- **Network errors**: Connection timeouts, DNS failures
- **Service unavailable**: Auto-mocks responses

### Graceful Degradation

When DocumentVault is unavailable:
1. Operations log warnings
2. Verification checks succeed automatically
3. Workflows continue normally
4. Returns mock responses with `mocked: true` flag

## Testing

### Unit Tests

Tests automatically handle DocumentVault unavailability:

```bash
pytest tests/test_properties.py tests/test_tokenization.py -v
```

All tests pass whether DocumentVault is configured or not.

### Integration Testing

To test with actual DocumentVault service:

1. Start DocumentVault service locally:
   ```bash
   cd /path/to/document-vault
   uvicorn app.main:app --port 8001
   ```

2. Configure EPR service:
   ```bash
   export DOCUMENT_VAULT_SERVICE_URL=http://localhost:8001
   ```

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

### Mock Testing

To test mocked behavior:

```bash
unset DOCUMENT_VAULT_SERVICE_URL
pytest tests/ -v
```

## Logging

All DocumentVault operations are logged with structured logging:

```python
# Successful verification
{
    "message": "document_vault_verify_success",
    "document_id": "uuid",
    "status": "verified"
}

# Mock response
{
    "message": "document_vault_verify_mock",
    "document_id": "uuid",
    "reason": "service_url_not_configured"
}

# Error
{
    "message": "document_vault_verify_http_error",
    "document_id": "uuid",
    "status_code": 500,
    "detail": "Internal Server Error"
}
```

## Production Deployment

### Prerequisites

1. DocumentVault service must be deployed and accessible
2. Network connectivity between EPR and DocumentVault services
3. Proper authentication/authorization if required

### Configuration

1. Add to environment variables:
   ```bash
   DOCUMENT_VAULT_SERVICE_URL=https://document-vault.omen.io
   ```

2. Restart EPR service:
   ```bash
   docker restart omen-epr
   ```

3. Verify connectivity:
   ```bash
   curl ${DOCUMENT_VAULT_SERVICE_URL}/health
   ```

### Monitoring

Monitor these metrics:
- DocumentVault API response times
- DocumentVault error rates
- Document verification success rates
- Network connectivity issues

### Timeouts

Default timeout: **30 seconds**

To adjust:
```python
from app.services.document_vault_client import DocumentVaultClient

client = DocumentVaultClient(timeout=60.0)  # 60 second timeout
```

## Troubleshooting

### Issue: "DocumentVault service URL not configured"

**Symptoms:** Warning logs indicating mock responses

**Solution:**
1. Set `DOCUMENT_VAULT_SERVICE_URL` environment variable
2. Restart application
3. Verify configuration: `echo $DOCUMENT_VAULT_SERVICE_URL`

### Issue: "Failed to connect to DocumentVault service"

**Symptoms:** `DocumentVaultError` exceptions in logs

**Possible Causes:**
1. DocumentVault service is down
2. Network connectivity issues
3. Incorrect URL configuration
4. Firewall blocking requests

**Solutions:**
1. Check DocumentVault service status
2. Verify network connectivity: `curl ${DOCUMENT_VAULT_SERVICE_URL}/health`
3. Check URL format (include protocol: http:// or https://)
4. Review firewall/security group rules

### Issue: Document verification always fails

**Symptoms:** Workflows blocked, documents not verified

**Possible Causes:**
1. Documents not uploaded to DocumentVault
2. Documents in wrong status
3. Entity ID mismatch

**Solutions:**
1. Check documents exist: `GET /api/v1/documents?entity_id={id}`
2. Verify document status in DocumentVault
3. Ensure entity IDs match between services

## API Reference

### DocumentVault Service Endpoints Used

#### Verify Document
```http
POST /api/v1/documents/verify
Content-Type: application/json

{
  "document_id": "uuid"
}
```

**Response:**
```json
{
  "document_id": "uuid",
  "status": "verified",
  "hash": "sha256-hash",
  "verified_at": "2025-11-12T00:00:00Z"
}
```

#### List Documents
```http
GET /api/v1/documents?entity_id={uuid}&status=verified
```

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "entity_id": "uuid",
      "document_type": "property_deed",
      "status": "verified",
      "created_at": "2025-11-12T00:00:00Z"
    }
  ],
  "count": 1,
  "offset": 0,
  "limit": 100
}
```

## Future Enhancements

### Planned Features

1. **Document Upload via EPR API**
   - Direct document upload through EPR endpoints
   - Proxy requests to DocumentVault

2. **Webhook Integration**
   - Receive verification status updates via webhooks
   - Automatic workflow triggering on document verification

3. **Batch Verification**
   - Verify multiple documents in single request
   - Improved performance for entities with many documents

4. **Document Caching**
   - Cache document verification status
   - Reduce API calls to DocumentVault

5. **Retry Logic**
   - Automatic retries on transient failures
   - Exponential backoff for rate limiting

### Configuration Extensions

Future configuration options:
```bash
# Authentication
DOCUMENT_VAULT_API_KEY=your-api-key
DOCUMENT_VAULT_CLIENT_ID=your-client-id

# Retry configuration
DOCUMENT_VAULT_MAX_RETRIES=3
DOCUMENT_VAULT_RETRY_DELAY=1

# Caching
DOCUMENT_VAULT_CACHE_TTL=300
```

## Related Documentation

- [DocumentVault Overview](./DOCUMENT_VAULT_OVERVIEW.md)
- [Tokenization Implementation Plan](./TOKENIZATION_IMPLEMENTATION_PLAN.md)
- [Workflow Orchestration](./WORKFLOW_ORCHESTRATION.md)
- [API Reference](./API_REFERENCE.md)


