"""Azure Service Bus wrapper for event-driven document processing"""
import logging
import json
from typing import Optional
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus.exceptions import ServiceBusError
from azure.identity import DefaultAzureCredential
from app.config import settings

logger = logging.getLogger(__name__)


class ServiceBusService:
    """Service Bus client for sending and receiving messages"""
    
    def __init__(self):
        """Initialize Service Bus client with managed identity or connection string"""
        self.queue_name = settings.service_bus_queue_name
        
        if settings.service_bus_connection_string:
            # Use connection string (for local development)
            self.client = ServiceBusClient.from_connection_string(
                settings.service_bus_connection_string
            )
            logger.info("Service Bus initialized with connection string")
        else:
            # Use managed identity (for Azure deployment)
            credential = DefaultAzureCredential()
            self.client = ServiceBusClient(
                fully_qualified_namespace=settings.service_bus_namespace,
                credential=credential
            )
            logger.info(f"Service Bus initialized with managed identity: {settings.service_bus_namespace}")
    
    async def send_document_message(self, engagement_id: str, document_id: str):
        """
        Send a message to the queue to trigger document processing
        
        Args:
            engagement_id: The engagement ID
            document_id: The document ID to process
        """
        try:
            sender = self.client.get_queue_sender(queue_name=self.queue_name)
            
            message_body = {
                "engagement_id": engagement_id,
                "document_id": document_id,
                "message_type": "document_processing"
            }
            
            message = ServiceBusMessage(
                body=json.dumps(message_body),
                content_type="application/json"
            )
            
            sender.send_messages(message)
            sender.close()
            
            logger.info(f"Sent Service Bus message for document {document_id}")
            
        except ServiceBusError as e:
            logger.error(f"Failed to send Service Bus message: {str(e)}")
            # Don't raise - worker will pick it up via fallback polling
    
    def receive_messages(self, max_wait_time: int = 60) -> list[dict]:
        """
        Receive messages from the queue
        
        Args:
            max_wait_time: Maximum time to wait for messages (seconds)
            
        Returns:
            List of message dictionaries with engagement_id and document_id
        """
        try:
            receiver = self.client.get_queue_receiver(
                queue_name=self.queue_name,
                max_wait_time=max_wait_time
            )
            
            messages = []
            with receiver:
                for msg in receiver:
                    try:
                        body = json.loads(str(msg))
                        messages.append({
                            "engagement_id": body.get("engagement_id"),
                            "document_id": body.get("document_id"),
                            "message": msg  # Keep reference for completion
                        })
                        logger.info(f"Received message for document {body.get('document_id')}")
                    except Exception as e:
                        logger.error(f"Failed to parse message: {str(e)}")
                        receiver.complete_message(msg)  # Remove bad message
            
            return messages
            
        except ServiceBusError as e:
            logger.error(f"Failed to receive Service Bus messages: {str(e)}")
            return []
    
    def complete_message(self, message):
        """Mark message as completed"""
        try:
            receiver = self.client.get_queue_receiver(queue_name=self.queue_name)
            with receiver:
                receiver.complete_message(message)
            logger.debug("Message completed successfully")
        except Exception as e:
            logger.error(f"Failed to complete message: {str(e)}")
    
    def abandon_message(self, message):
        """Abandon message (will be retried)"""
        try:
            receiver = self.client.get_queue_receiver(queue_name=self.queue_name)
            with receiver:
                receiver.abandon_message(message)
            logger.debug("Message abandoned for retry")
        except Exception as e:
            logger.error(f"Failed to abandon message: {str(e)}")
    
    def close(self):
        """Close the Service Bus client"""
        try:
            self.client.close()
            logger.info("Service Bus client closed")
        except Exception as e:
            logger.error(f"Failed to close Service Bus client: {str(e)}")


# Singleton instance
_service_bus_service: Optional[ServiceBusService] = None


def get_service_bus() -> Optional[ServiceBusService]:
    """
    Get or create Service Bus service instance
    
    Returns None if Service Bus is not configured (falls back to polling)
    """
    global _service_bus_service
    
    # Only initialize if Service Bus is configured
    if not settings.service_bus_enabled:
        return None
    
    if _service_bus_service is None:
        try:
            _service_bus_service = ServiceBusService()
        except Exception as e:
            logger.error(f"Failed to initialize Service Bus: {str(e)}")
            logger.warning("Falling back to database polling for document processing")
            return None
    
    return _service_bus_service
