"""API routes for engagement management"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db_session import get_session
from app.database import Engagement, Document
from app.models import EngagementCreate, EngagementResponse
from app.services.vector_store import get_vector_store
from datetime import datetime

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


@router.delete("/{engagement_id}", status_code=204)
async def delete_engagement(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete an engagement and all its documents"""
    engagement = await session.get(Engagement, engagement_id)
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Delete from vector store
    vector_store = get_vector_store()
    await vector_store.delete_collection(engagement_id)
    
    # Delete from database (cascade will delete documents and Q&A history)
    await session.delete(engagement)
    await session.commit()
    
    return None
