#!/usr/bin/env python3
"""Manually trigger processing for queued documents via Service Bus"""
import asyncio
import sys
from sqlalchemy import select
from app.db_session import get_session
from app.database import Document
from app.services.service_bus import get_service_bus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def trigger_queued_documents(engagement_id: str):
    """Send Service Bus messages for all queued documents"""
    service_bus = get_service_bus()
    if not service_bus:
        logger.error("Service Bus not configured!")
        return
    
    async for session in get_session():
        try:
            # Get all queued documents
            result = await session.execute(
                select(Document).where(
                    Document.engagement_id == engagement_id,
                    Document.status == 'queued'
                )
            )
            queued_docs = result.scalars().all()
            
            logger.info(f"Found {len(queued_docs)} queued documents")
            
            sent = 0
            for doc in queued_docs:
                try:
                    await service_bus.send_document_message(
                        str(doc.engagement_id),
                        str(doc.id)
                    )
                    sent += 1
                    logger.info(f"✅ Sent message for: {doc.filename}")
                except Exception as e:
                    logger.error(f"❌ Failed to send message for {doc.filename}: {e}")
            
            logger.info(f"✅ Sent {sent}/{len(queued_docs)} messages to Service Bus")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await session.close()
            break

if __name__ == "__main__":
    engagement_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not engagement_id:
        print("Usage: python trigger_processing.py <engagement_id>")
        sys.exit(1)
    
    asyncio.run(trigger_queued_documents(engagement_id))
