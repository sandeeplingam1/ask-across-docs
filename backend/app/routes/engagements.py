"""API routes for engagement management"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db_session import get_session
from app.database import Engagement, Document
from app.models import EngagementCreate, EngagementResponse
from app.services.vector_store import get_vector_store
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engagements", tags=["engagements"])


@router.post("", response_model=EngagementResponse, status_code=201)
async def create_engagement(
    engagement_data: EngagementCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new engagement"""
    engagement = Engagement(
        name=engagement_data.name,
        description=engagement_data.description,
        client_name=engagement_data.client_name,
        start_date=engagement_data.start_date,
        end_date=engagement_data.end_date
    )
    
    session.add(engagement)
    await session.commit()
    await session.refresh(engagement)
    
    # Create vector store collection for this engagement
    vector_store = get_vector_store()
    await vector_store.create_collection(engagement.id)
    
    return EngagementResponse(
        id=engagement.id,
        name=engagement.name,
        description=engagement.description,
        client_name=engagement.client_name,
        start_date=engagement.start_date,
        end_date=engagement.end_date,
        document_count=0,
        created_at=engagement.created_at,
        updated_at=engagement.updated_at
    )


@router.get("", response_model=list[EngagementResponse])
async def list_engagements(
    session: AsyncSession = Depends(get_session)
):
    """List all engagements with document counts"""
    # Get engagements with document counts
    # SQL Server requires all non-aggregated columns in GROUP BY
    query = (
        select(
            Engagement,
            func.count(Document.id).label("document_count")
        )
        .outerjoin(Document, Engagement.id == Document.engagement_id)
        .group_by(
            Engagement.id,
            Engagement.name,
            Engagement.description,
            Engagement.client_name,
            Engagement.start_date,
            Engagement.end_date,
            Engagement.created_at,
            Engagement.updated_at
        )
        .order_by(Engagement.created_at.desc())
    )
    
    result = await session.execute(query)
    rows = result.all()
    
    return [
        EngagementResponse(
            id=row.Engagement.id,
            name=row.Engagement.name,
            description=row.Engagement.description,
            client_name=row.Engagement.client_name,
            start_date=row.Engagement.start_date,
            end_date=row.Engagement.end_date,
            document_count=row.document_count,
            created_at=row.Engagement.created_at,
            updated_at=row.Engagement.updated_at
        )
        for row in rows
    ]


@router.get("/{engagement_id}", response_model=EngagementResponse)
async def get_engagement(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get engagement details"""
    engagement = await session.get(Engagement, engagement_id)
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Count documents
    doc_count_query = select(func.count(Document.id)).where(
        Document.engagement_id == engagement_id
    )
    result = await session.execute(doc_count_query)
    document_count = result.scalar()
    
    return EngagementResponse(
        id=engagement.id,
        name=engagement.name,
        description=engagement.description,
        client_name=engagement.client_name,
        start_date=engagement.start_date,
        end_date=engagement.end_date,
        document_count=document_count,
        created_at=engagement.created_at,
        updated_at=engagement.updated_at
    )


@router.put("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    engagement_id: str,
    engagement_data: EngagementCreate,
    session: AsyncSession = Depends(get_session)
):
    """Update an existing engagement"""
    engagement = await session.get(Engagement, engagement_id)
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Update fields
    engagement.name = engagement_data.name
    engagement.description = engagement_data.description
    engagement.client_name = engagement_data.client_name
    engagement.start_date = engagement_data.start_date
    engagement.end_date = engagement_data.end_date
    engagement.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(engagement)
    
    # Count documents
    doc_count_query = select(func.count(Document.id)).where(
        Document.engagement_id == engagement_id
    )
    result = await session.execute(doc_count_query)
    document_count = result.scalar()
    
    return EngagementResponse(
        id=engagement.id,
        name=engagement.name,
        description=engagement.description,
        client_name=engagement.client_name,
        start_date=engagement.start_date,
        end_date=engagement.end_date,
        document_count=document_count,
        created_at=engagement.created_at,
        updated_at=engagement.updated_at
    )


@router.delete("/{engagement_id}", status_code=204)
async def delete_engagement(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete an engagement and all its documents, blob files, and vector embeddings"""
    engagement = await session.get(Engagement, engagement_id)
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Get all documents for this engagement to delete their files
    doc_query = select(Document).where(Document.engagement_id == engagement_id)
    result = await session.execute(doc_query)
    documents = result.scalars().all()
    
    # Delete physical files from disk/blob storage
    deleted_files = 0
    for doc in documents:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
                deleted_files += 1
                logger.info(f"Deleted file: {doc.file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {doc.file_path}: {str(e)}")
    
    # Delete from vector store (AI Search)
    vector_store = get_vector_store()
    await vector_store.delete_collection(engagement_id)
    logger.info(f"Deleted vector collection for engagement: {engagement_id}")
    
    # Delete from database (cascade will delete documents and Q&A history)
    await session.delete(engagement)
    await session.commit()
    
    logger.info(f"Deleted engagement {engagement_id} with {len(documents)} documents ({deleted_files} files)")
    return None
