"""
Admin utility routes for managing documents and troubleshooting
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Document
from app.db_session import get_session
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/documents/reset-stuck")
async def reset_stuck_documents(
    max_age_minutes: int = 10,
    db: AsyncSession = Depends(get_session)
):
    """
    Reset documents stuck in 'processing' status.
    
    Finds documents that are:
    - status = 'processing' AND
    - (processing_started_at is NULL OR processing_started_at > max_age_minutes ago)
    
    Resets them to 'queued' status for worker to retry.
    """
    try:
        threshold = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        # Find stuck documents
        query = select(Document).where(
            Document.status == "processing"
        )
        
        result = await db.execute(query)
        all_processing = result.scalars().all()
        
        stuck_docs = []
        for doc in all_processing:
            # Check if started_at is None or too old
            if doc.processing_started_at is None or doc.processing_started_at < threshold:
                stuck_docs.append(doc)
        
        if not stuck_docs:
            return {
                "success": True,
                "message": "No stuck documents found",
                "reset_count": 0
            }
        
        # Reset each stuck document
        reset_ids = []
        for doc in stuck_docs:
            logger.info(f"Resetting stuck document: {doc.id} - {doc.filename}")
            doc.status = "queued"
            doc.progress = 0
            doc.error_message = None
            doc.processing_started_at = None
            reset_ids.append(str(doc.id))
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Reset {len(stuck_docs)} stuck documents to queued status",
            "reset_count": len(stuck_docs),
            "reset_document_ids": reset_ids
        }
        
    except Exception as e:
        logger.error(f"Error resetting stuck documents: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset documents: {str(e)}")


@router.get("/documents/status-summary")
async def get_document_status_summary(
    engagement_id: str = None,
    db: AsyncSession = Depends(get_session)
):
    """Get summary of document statuses across all engagements or for specific engagement"""
    try:
        query = select(Document)
        if engagement_id:
            query = query.where(Document.engagement_id == engagement_id)
        
        result = await db.execute(query)
        docs = result.scalars().all()
        
        summary = {
            "total": len(docs),
            "by_status": {},
            "stuck_processing": 0,
            "stuck_document_ids": []
        }
        
        threshold = datetime.utcnow() - timedelta(minutes=10)
        
        for doc in docs:
            status = doc.status
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Check for stuck processing
            if status == "processing":
                if doc.processing_started_at is None or doc.processing_started_at < threshold:
                    summary["stuck_processing"] += 1
                    summary["stuck_document_ids"].append({
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "started_at": doc.processing_started_at.isoformat() if doc.processing_started_at else None
                    })
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting status summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
