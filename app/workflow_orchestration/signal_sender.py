"""Send signals to running Temporal workflows."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from temporalio.client import Client, WorkflowHandle

from app.workflow_orchestration.client import get_temporal_client
from app.workflow_orchestration.config import TemporalConfig, get_temporal_config

logger = logging.getLogger("app.workflow.signal_sender")


class WorkflowSignalSender:
    """Send signals to running Temporal workflows."""
    
    def __init__(self, config: Optional[TemporalConfig] = None) -> None:
        """Initialize signal sender."""
        self._config = config or get_temporal_config()
        self._client: Optional[Client] = None
    
    async def _get_client(self) -> Client:
        """Get or create Temporal client."""
        if self._client is None:
            self._client = await get_temporal_client(self._config)
        return self._client
    
    async def send_signal(
        self,
        workflow_id: str,
        signal_name: str,
        signal_arg: Any = None,
    ) -> bool:
        """
        Send signal to a running workflow.
        
        Args:
            workflow_id: Workflow ID to send signal to
            signal_name: Name of the signal method
            signal_arg: Argument to pass to the signal
        
        Returns:
            True if signal sent successfully, False otherwise
        """
        if not self._config.enabled:
            logger.warning(
                "temporal_disabled_skipping_signal",
                extra={
                    "workflow_id": workflow_id,
                    "signal_name": signal_name,
                },
            )
            return False
        
        logger.info(
            "attempting_to_send_signal",
            extra={
                "workflow_id": workflow_id,
                "signal_name": signal_name,
                "has_signal_arg": signal_arg is not None,
            },
        )
        
        try:
            client = await self._get_client()
            logger.info(
                "temporal_client_connected",
                extra={
                    "workflow_id": workflow_id,
                    "host": self._config.host,
                    "namespace": self._config.namespace,
                },
            )
            
            handle: WorkflowHandle = client.get_workflow_handle(workflow_id)
            
            logger.info(
                "workflow_handle_obtained",
                extra={
                    "workflow_id": workflow_id,
                    "signal_name": signal_name,
                },
            )
            
            if signal_arg is not None:
                await handle.signal(signal_name, signal_arg)
                logger.info(
                    "signal_sent_with_args",
                    extra={
                        "workflow_id": workflow_id,
                        "signal_name": signal_name,
                        "signal_arg_keys": list(signal_arg.keys()) if isinstance(signal_arg, dict) else None,
                    },
                )
            else:
                await handle.signal(signal_name)
                logger.info(
                    "signal_sent_no_args",
                    extra={
                        "workflow_id": workflow_id,
                        "signal_name": signal_name,
                    },
                )
            
            logger.info(
                "workflow_signal_sent_successfully",
                extra={
                    "workflow_id": workflow_id,
                    "signal_name": signal_name,
                },
            )
            return True
        
        except Exception as exc:
            logger.error(
                "workflow_signal_failed",
                extra={
                    "workflow_id": workflow_id,
                    "signal_name": signal_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            return False
    
    async def send_document_verified_signal(
        self,
        entity_id: str,
        entity_type: str,
        verification_data: Dict[str, Any],
    ) -> bool:
        """
        Send document_verified signal to appropriate workflow.
        
        Args:
            entity_id: Entity ID (property, investor, etc.)
            entity_type: Type of entity (issuer, investor, etc.)
            verification_data: Verification result data
        
        Returns:
            True if signal sent successfully
        """
        # Determine workflow ID based on entity type
        if entity_type in ["issuer", "property", "offering"]:
            workflow_id = f"property-onboarding-{entity_id}"
            signal_name = "document_verified_signal"
        elif entity_type == "investor":
            workflow_id = f"investor-onboarding-{entity_id}"
            signal_name = "kyc_documents_uploaded_signal"
        else:
            logger.warning(
                "unknown_entity_type_for_signal",
                extra={"entity_id": entity_id, "entity_type": entity_type},
            )
            return False
        
        logger.info(
            "sending_document_verified_signal",
            extra={
                "entity_id": entity_id,
                "entity_type": entity_type,
                "workflow_id": workflow_id,
            },
        )
        
        return await self.send_signal(
            workflow_id=workflow_id,
            signal_name=signal_name,
            signal_arg=verification_data,
        )


# Singleton instance
_signal_sender: Optional[WorkflowSignalSender] = None


def get_signal_sender() -> WorkflowSignalSender:
    """Get or create workflow signal sender singleton."""
    global _signal_sender
    if _signal_sender is None:
        _signal_sender = WorkflowSignalSender()
    return _signal_sender
