"""Real-time document processing progress endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db_session import get_session
from app.database import Document
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engagements/{engagement_id}/progress", tags=["progress"])


@router.get("")
async def get_processing_progress(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Get real-time processing progress for all documents in an engagement.
    Returns detailed status, progress percentages, and estimated time remaining.
    """
    # Get all documents with their status and progress
    query = select(Document).where(
        Document.engagement_id == engagement_id
    ).order_by(Document.uploaded_at.desc())
    
    result = await session.execute(query)
    documents = result.scalars().all()
    
    if not documents:
        return {
            "total_documents": 0,
            "completed": 0,
            "processing": 0,
            "queued": 0,
            "failed": 0,
            "overall_progress": 0,
            "estimated_time_remaining_seconds": 0,
            "documents": []
        }
    
    # Calculate statistics
    status_counts = {
        "completed": 0,
        "processing": 0,
        "queued": 0,
        "failed": 0
    }
    
    total_progress = 0
    processing_docs = []
    
    for doc in documents:
        status_counts[doc.status] = status_counts.get(doc.status, 0) + 1
        
        if doc.status == "completed":
            total_progress += 100
        elif doc.status == "processing":
            total_progress += doc.progress
            processing_docs.append({
                "id": doc.id,
                "filename": doc.filename,
                "progress": doc.progress,
                "status_detail": _get_status_detail(doc.progress)
            })
        # queued and failed contribute 0 to progress
    
    total_docs = len(documents)
    overall_progress = int(total_progress / total_docs) if total_docs > 0 else 0
    
    # Estimate time remaining (assuming ~5 minutes per document)
    remaining_docs = status_counts["queued"] + status_counts["processing"]
    estimated_seconds = remaining_docs * 300  # 5 minutes = 300 seconds
    
    # Build detailed document list
    document_list = []
    for doc in documents:
        doc_info = {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "progress": doc.progress,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "chunk_count": doc.chunk_count
        }
        
        if doc.status == "processing":
            doc_info["status_detail"] = _get_status_detail(doc.progress)
            if doc.processing_started_at:
                doc_info["processing_started_at"] = doc.processing_started_at.isoformat()
        
        if doc.status == "failed":
            doc_info["error_message"] = doc.error_message
        
        document_list.append(doc_info)
    
    return {
        "total_documents": total_docs,
        "completed": status_counts["completed"],
        "processing": status_counts["processing"],
        "queued": status_counts["queued"],
        "failed": status_counts["failed"],
        "overall_progress": overall_progress,
        "estimated_time_remaining_seconds": estimated_seconds,
        "currently_processing": processing_docs,
        "documents": document_list
    }


def _get_status_detail(progress: int) -> str:
    """Get human-readable status detail based on progress percentage"""
    if progress < 15:
        return "Downloading document..."
    elif progress < 30:
        return "Extracting text..."
    elif progress < 55:
        return "Chunking content..."
    elif progress < 75:
        return "Generating embeddings..."
    elif progress < 95:
        return "Indexing in search..."
    else:
        return "Finalizing..."
