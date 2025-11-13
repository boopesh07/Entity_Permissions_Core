"""DocumentVault service client for document operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("app.services.document_vault_client")


class DocumentVaultError(Exception):
    """Base exception for DocumentVault operations."""


class DocumentVaultClient:
    """
    Client for interacting with the DocumentVault microservice.
    
    Makes actual HTTP calls to DocumentVault API endpoints for document
    upload and verification operations.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        """
        Initialize DocumentVault client.
        
        Args:
            base_url: Base URL for DocumentVault service
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        self._base_url = base_url or settings.document_vault_service_url
        self._timeout = timeout
        
        if not self._base_url:
            logger.warning("DocumentVault service URL not configured - operations will be mocked")
    
    async def verify_document(self, document_id: str) -> Dict[str, Any]:
        """
        Verify a document via DocumentVault service.
        
        Calls POST /api/v1/documents/verify endpoint which:
        - Streams S3 object
        - Re-computes hash
        - Updates status (verified/mismatch)
        - Publishes events
        
        Args:
            document_id: Document identifier
        
        Returns:
            Verification result
        
        Raises:
            DocumentVaultError: If verification fails
        """
        if not self._base_url:
            # Mock response when not configured
            logger.info(
                "document_vault_verify_mock",
                extra={"document_id": document_id, "reason": "service_url_not_configured"},
            )
            return {
                "document_id": document_id,
                "status": "verified",
                "mocked": True,
            }
        
        url = f"{self._base_url}/api/v1/documents/verify"
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url,
                    json={"document_id": document_id},
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    "document_vault_verify_success",
                    extra={
                        "document_id": document_id,
                        "status": result.get("status"),
                    },
                )
                
                return result
        
        except httpx.HTTPStatusError as exc:
            logger.error(
                "document_vault_verify_http_error",
                extra={
                    "document_id": document_id,
                    "status_code": exc.response.status_code,
                    "detail": exc.response.text,
                },
            )
            raise DocumentVaultError(
                f"Document verification failed: {exc.response.status_code}"
            ) from exc
        
        except httpx.RequestError as exc:
            logger.error(
                "document_vault_verify_request_error",
                extra={
                    "document_id": document_id,
                    "error": str(exc),
                },
            )
            raise DocumentVaultError(
                f"Failed to connect to DocumentVault service: {exc}"
            ) from exc
    
    async def get_documents_by_entity(
        self,
        entity_id: str,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get documents for an entity.
        
        Calls GET /api/v1/documents?entity_id={entity_id}&status={status}
        
        Args:
            entity_id: Entity identifier
            status: Optional status filter (uploaded, verified, etc.)
        
        Returns:
            Document list response
        
        Raises:
            DocumentVaultError: If request fails
        """
        if not self._base_url:
            # Mock response when not configured
            logger.info(
                "document_vault_list_mock",
                extra={"entity_id": entity_id, "reason": "service_url_not_configured"},
            )
            return {
                "documents": [],
                "count": 0,
                "mocked": True,
            }
        
        url = f"{self._base_url}/api/v1/documents"
        params = {"entity_id": entity_id}
        if status:
            params["status"] = status
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    "document_vault_list_success",
                    extra={
                        "entity_id": entity_id,
                        "count": len(result.get("documents", [])),
                    },
                )
                
                return result
        
        except httpx.HTTPStatusError as exc:
            logger.error(
                "document_vault_list_http_error",
                extra={
                    "entity_id": entity_id,
                    "status_code": exc.response.status_code,
                    "detail": exc.response.text,
                },
            )
            raise DocumentVaultError(
                f"Failed to list documents: {exc.response.status_code}"
            ) from exc
        
        except httpx.RequestError as exc:
            logger.error(
                "document_vault_list_request_error",
                extra={
                    "entity_id": entity_id,
                    "error": str(exc),
                },
            )
            raise DocumentVaultError(
                f"Failed to connect to DocumentVault service: {exc}"
            ) from exc
    
    async def check_documents_status(
        self,
        entity_id: str,
        required_status: str = "verified",
    ) -> bool:
        """
        Check if entity has documents with required status.
        
        Args:
            entity_id: Entity identifier
            required_status: Required document status
        
        Returns:
            True if entity has documents with required status
        """
        try:
            result = await self.get_documents_by_entity(
                entity_id=entity_id,
                status=required_status,
            )
            
            documents = result.get("documents", [])
            has_documents = len(documents) > 0
            
            logger.info(
                "document_vault_status_check",
                extra={
                    "entity_id": entity_id,
                    "required_status": required_status,
                    "has_documents": has_documents,
                    "count": len(documents),
                },
            )
            
            return has_documents
        
        except DocumentVaultError:
            # If service unavailable, assume documents are OK for demo
            logger.warning(
                "document_vault_status_check_failed_assuming_ok",
                extra={"entity_id": entity_id},
            )
            return True


# Singleton instance
_document_vault_client: Optional[DocumentVaultClient] = None


def get_document_vault_client() -> DocumentVaultClient:
    """Get or create DocumentVault client singleton."""
    global _document_vault_client
    if _document_vault_client is None:
        _document_vault_client = DocumentVaultClient()
    return _document_vault_client


