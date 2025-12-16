"""Reset stuck documents and resend to Service Bus queue"""
import asyncio
import sys
from sqlalchemy import select, update
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Document
from app.services.service_bus import get_service_bus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_stuck_documents(engagement_id: str = None, hours_stuck: int = 1):
    """
    Reset documents that have been stuck in processing/queued for too long
    and resend them to Service Bus
    """
    db = next(get_db())
    service_bus = get_service_bus()
    
    if not service_bus:
        logger.error("Service Bus not configured!")
        return
    
    try:
        # Find stuck documents
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_stuck)
        
        query = select(Document).where(
            Document.status.in_(['processing', 'queued']),
            Document.updated_at < cutoff_time
        )
        
        if engagement_id:
            query = query.where(Document.engagement_id == engagement_id)
        
        stuck_docs = db.execute(query).scalars().all()
        
        if not stuck_docs:
            logger.info("No stuck documents found")
            return
        
        logger.info(f"Found {len(stuck_docs)} stuck documents")
        
        # Reset and resend each document
        for doc in stuck_docs:
            logger.info(f"Resetting: {doc.filename} (Status: {doc.status})")
            
            # Reset to queued
            doc.status = 'queued'
            doc.updated_at = datetime.utcnow()
            db.commit()
            
            # Resend to Service Bus
            try:
                await service_bus.send_document_message(
                    str(doc.engagement_id),
                    str(doc.id)
                )
                logger.info(f"✅ Resent to queue: {doc.filename}")
            except Exception as e:
                logger.error(f"❌ Failed to resend {doc.filename}: {e}")
        
        logger.info(f"✅ Reset {len(stuck_docs)} documents and resent to queue")
        
    except Exception as e:
        logger.error(f"Error resetting stuck documents: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    engagement_id = sys.argv[1] if len(sys.argv) > 1 else None
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    asyncio.run(reset_stuck_documents(engagement_id, hours))
