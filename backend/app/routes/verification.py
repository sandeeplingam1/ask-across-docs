"""Document verification endpoints - verify chunks are actually in AI Search"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db_session import get_session
from app.database import Document
from app.services.vector_store import get_vector_store
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engagements/{engagement_id}", tags=["verification"])


@router.get("/documents/verify-indexing")
async def verify_document_indexing(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Verify that completed documents actually have chunks in AI Search.
    
    Returns:
    - documents: List of documents with DB chunk count vs AI Search count
    - summary: Overall statistics
    - issues: Documents with mismatches
    """
    try:
        # Get all completed documents for this engagement
        query = select(Document).where(
            Document.engagement_id == engagement_id,
            Document.status == "completed"
        )
        result = await session.execute(query)
        documents = result.scalars().all()
        
        if not documents:
            return {
                "summary": {
                    "total_documents": 0,
                    "verified": 0,
                    "missing_chunks": 0,
                    "mismatch": 0
                },
                "documents": [],
                "issues": []
            }
        
        # Get vector store
        vector_store = await get_vector_store()
        
        verification_results = []
        issues = []
        verified_count = 0
        missing_count = 0
        mismatch_count = 0
        
        for doc in documents:
            # Query AI Search for chunks with this document_id
            try:
                # Search for chunks belonging to this document
                search_results = await vector_store.search(
                    query_text="*",  # Match all
                    filter_expression=f"document_id eq '{doc.id}'",
                    top_k=1000,  # Get all chunks
                    include_embeddings=False
                )
                
                ai_search_count = len(search_results)
                db_chunk_count = doc.chunk_count or 0
                
                status = "verified"
                if ai_search_count == 0:
                    status = "missing"
                    missing_count += 1
                    issues.append({
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "issue": "No chunks found in AI Search",
                        "db_chunks": db_chunk_count,
                        "ai_search_chunks": 0
                    })
                elif ai_search_count != db_chunk_count:
                    status = "mismatch"
                    mismatch_count += 1
                    issues.append({
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "issue": "Chunk count mismatch",
                        "db_chunks": db_chunk_count,
                        "ai_search_chunks": ai_search_count
                    })
                else:
                    verified_count += 1
                
                verification_results.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "status": status,
                    "db_chunk_count": db_chunk_count,
                    "ai_search_chunk_count": ai_search_count,
                    "match": ai_search_count == db_chunk_count and ai_search_count > 0
                })
                
            except Exception as e:
                logger.error(f"Error verifying document {doc.id}: {str(e)}")
                issues.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "issue": f"Verification error: {str(e)}",
                    "db_chunks": doc.chunk_count or 0,
                    "ai_search_chunks": "error"
                })
        
        return {
            "summary": {
                "total_documents": len(documents),
                "verified": verified_count,
                "missing_chunks": missing_count,
                "mismatch": mismatch_count,
                "percentage_verified": round((verified_count / len(documents)) * 100, 1) if documents else 0
            },
            "documents": verification_results,
            "issues": issues
        }
        
    except Exception as e:
        logger.error(f"Error in verify_document_indexing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/verify")
async def verify_single_document(
    engagement_id: str,
    document_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Verify a single document's chunks are in AI Search.
    Returns sample chunks for inspection.
    """
    try:
        # Get document
        query = select(Document).where(
            Document.id == document_id,
            Document.engagement_id == engagement_id
        )
        result = await session.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get vector store
        vector_store = await get_vector_store()
        
        # Search for chunks
        search_results = await vector_store.search(
            query_text="*",
            filter_expression=f"document_id eq '{document_id}'",
            top_k=10,  # Get sample of first 10 chunks
            include_embeddings=False
        )
        
        return {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status,
            "db_chunk_count": document.chunk_count or 0,
            "ai_search_chunk_count_sample": len(search_results),
            "chunks_exist": len(search_results) > 0,
            "sample_chunks": [
                {
                    "chunk_index": chunk.get("chunk_index", 0),
                    "text_preview": chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", ""),
                    "page_number": chunk.get("page_number")
                }
                for chunk in search_results[:5]  # Show first 5
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying single document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
