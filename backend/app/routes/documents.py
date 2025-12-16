"""API routes for document upload and management"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from app.db_session import get_session
from app.database import Engagement, Document
from app.models import DocumentResponse, MultiUploadResponse, UploadStatus
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import get_vector_store
from app.services.file_storage import get_file_storage
from app.services.background_tasks import BackgroundDocumentProcessor
from app.services.service_bus import get_service_bus
from app.config import settings
from datetime import datetime, timedelta
import os
import aiofiles
from pathlib import Path
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/engagements/{engagement_id}/documents", tags=["documents"])

# Initialize services
doc_processor = DocumentProcessor(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap
)
embedding_service = EmbeddingService()
vector_store = get_vector_store()
background_processor = BackgroundDocumentProcessor()


@router.post("", response_model=MultiUploadResponse)
async def upload_documents(
    engagement_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session)
):
    """Upload multiple documents to an engagement"""
    # Verify engagement exists
    engagement = await session.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Create upload directory
    upload_dir = Path(f"./data/uploads/{engagement_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    successful = 0
    failed = 0
    
    for file in files:
        try:
            # Validate file type
            if not doc_processor.is_supported(file.filename):
                results.append(UploadStatus(
                    filename=file.filename,
                    status="failed",
                    message=f"Unsupported file type. Supported: PDF, DOCX, TXT"
                ))
                failed += 1
                continue
            
            # Validate file size
            file_content = await file.read()
            file_size = len(file_content)
            max_size = settings.max_upload_size_mb * 1024 * 1024
            
            if file_size > max_size:
                results.append(UploadStatus(
                    filename=file.filename,
                    status="failed",
                    message=f"File too large. Max size: {settings.max_upload_size_mb}MB"
                ))
                failed += 1
                continue
            
            # Save file using storage service
            file_storage = get_file_storage()
            file_path = await file_storage.save_file(
                file_content,
                engagement_id,
                file.filename
            )
            
            # Create document record - queue for processing
            document = Document(
                engagement_id=engagement_id,
                filename=file.filename,
                file_type=doc_processor.get_file_type(file.filename),
                file_size=file_size,
                file_path=str(file_path),
                status="queued"  # Queue initially for batch processing
            )
            
            session.add(document)
            await session.flush()  # Get document ID
            
            logger.info(f"Document {document.id} queued for processing")
            
            # Send Service Bus message for immediate processing (if enabled)
            try:
                from app.services.service_bus import get_service_bus
                service_bus = get_service_bus()
                if service_bus:
                    await service_bus.send_document_message(engagement_id, str(document.id))
                    logger.info(f"Sent Service Bus message for document {document.id}")
            except Exception as e:
                logger.warning(f"Failed to send Service Bus message (will use polling fallback): {str(e)}")
            
            results.append(UploadStatus(
                filename=file.filename,
                status="queued",
                message="Uploaded successfully. Processing will start automatically.",
                document_id=document.id
            ))
            successful += 1

        except Exception as e:
            logger.error(f"Upload error for {file.filename}: {str(e)}", exc_info=True)
            results.append(UploadStatus(
                filename=file.filename,
                status="failed",
                message=f"Upload error: {str(e)}"
            ))
            failed += 1
    
    await session.commit()
    
    return MultiUploadResponse(
        total_files=len(files),
        successful=successful,
        failed=failed,
        results=results
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """List all documents in an engagement"""
    query = select(Document).where(
        Document.engagement_id == engagement_id
    ).order_by(Document.uploaded_at.desc())
    
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    engagement_id: str,
    document_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete a document completely - from vector store, storage, and database"""
    document = await session.get(Document, document_id)
    
    if not document or document.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # 1. Delete from vector store (AI Search) - removes embeddings
        logger.info(f"Deleting document {document_id} from vector store")
        await vector_store.delete_document(engagement_id, document_id)
        
        # 2. Delete file from storage (Azure Blob or local)
        if document.file_path:
            try:
                file_storage = get_file_storage()
                await file_storage.delete_file(document.file_path)
                logger.info(f"Deleted file from storage: {document.file_path}")
            except Exception as e:
                logger.warning(f"Could not delete file from storage: {str(e)}")
                # Continue anyway - database cleanup is most important
        
        # 3. Delete from database
        await session.delete(document)
        await session.commit()
        
        logger.info(f"Successfully deleted document {document_id}")
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
    
    return None


@router.post("/process-queued", status_code=202)
async def process_queued_documents(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Process all queued documents for an engagement"""
    # Get all queued documents
    query = select(Document).where(
        Document.engagement_id == engagement_id,
        Document.status == "queued"
    )
    
    result = await session.execute(query)
    queued_docs = result.scalars().all()
    
    if not queued_docs:
        return {"message": "No documents to process", "count": 0}


@router.post("/reset-stuck", status_code=200)
async def reset_stuck_documents(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Reset documents stuck in processing status back to queued"""
    from datetime import datetime, timedelta
    
    # Find documents stuck in processing for more than 5 minutes
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    
    query = select(Document).where(
        Document.engagement_id == engagement_id,
        Document.status == "processing",
        Document.updated_at < five_minutes_ago
    )
    
    result = await session.execute(query)
    stuck_docs = result.scalars().all()
    
    if not stuck_docs:
        return {
            "message": "No stuck documents found",
            "reset_count": 0
        }
    
    # Reset them to queued
    for doc in stuck_docs:
        doc.status = "queued"
        doc.progress = 0
        doc.error_message = "Reset from stuck processing state"
        logger.info(f"Reset stuck document {doc.id} ({doc.filename}) to queued")
    
    await session.commit()
    
    return {
        "message": f"Reset {len(stuck_docs)} stuck documents",
        "reset_count": len(stuck_docs),
        "documents": [{"id": doc.id, "filename": doc.filename} for doc in stuck_docs]
    }


@router.post("/process-queued-old", status_code=202)
async def process_queued_documents_old(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """OLD DEPRECATED: Process all queued documents for an engagement"""
    
    processed = 0
    failed = 0
    
    for document in queued_docs:
        try:
            document.status = "processing"
            await session.commit()
            
            # Read file content
            async with aiofiles.open(document.file_path, 'rb') as f:
                file_content = await f.read()
            
            # Extract text
            from io import BytesIO
            extraction_result = doc_processor.extract_with_metadata(BytesIO(file_content), document.filename)
            text = extraction_result['text']
            pages_info = extraction_result['pages']
            
            if not text.strip():
                raise ValueError("No text extracted from document")
            
            # Chunk text
            chunks = doc_processor.chunk_text(
                text,
                metadata={
                    "document_id": document.id,
                    "filename": document.filename,
                    "engagement_id": engagement_id
                },
                pages_info=pages_info
            )
            
            # Generate embeddings
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await embedding_service.embed_batch(chunk_texts)
            
            # Store in vector database
            await vector_store.add_documents(
                engagement_id=engagement_id,
                document_id=document.id,
                chunks=chunks,
                embeddings=embeddings
            )
            
            # Update document status
            document.status = "completed"
            document.chunk_count = len(chunks)
            document.progress = 100
            processed += 1
            
        except Exception as e:
            logger.error(f"Failed to process document {document.id}: {str(e)}")
            document.status = "failed"
            document.error_message = str(e)
            failed += 1
        
        await session.commit()
    
    return {
        "message": f"Processing complete",
        "total": len(queued_docs),
        "processed": processed,
        "failed": failed
    }


@router.post("/{engagement_id}/reset-stuck", tags=["admin"])
async def reset_stuck_documents(
    engagement_id: str,
    hours_stuck: int = 1,
    session: AsyncSession = Depends(get_session)
):
    """Reset documents stuck in processing/queued for too long and resend to Service Bus"""
    logger.info(f"Resetting stuck documents for engagement {engagement_id} (stuck > {hours_stuck} hours)")
    
    # Verify engagement exists
    engagement = await session.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Get Service Bus
    service_bus = get_service_bus()
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service Bus not configured")
    
    # Find stuck documents
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_stuck)
    
    result = await session.execute(
        select(Document).where(
            Document.engagement_id == engagement_id,
            Document.status.in_(['processing', 'queued']),
            Document.updated_at < cutoff_time
        )
    )
    stuck_docs = result.scalars().all()
    
    if not stuck_docs:
        return {"message": "No stuck documents found", "reset_count": 0}
    
    logger.info(f"Found {len(stuck_docs)} stuck documents")
    
    reset_count = 0
    failed_count = 0
    
    # Reset and resend each document
    for doc in stuck_docs:
        try:
            logger.info(f"Resetting: {doc.filename} (Status: {doc.status})")
            
            # Reset to queued
            doc.status = 'queued'
            doc.updated_at = datetime.utcnow()
            doc.error_message = None
            
            # Resend to Service Bus
            await service_bus.send_document_message(str(doc.engagement_id), str(doc.id))
            
            reset_count += 1
            logger.info(f"✅ Reset and resent: {doc.filename}")
            
        except Exception as e:
            failed_count += 1
            logger.error(f"❌ Failed to reset {doc.filename}: {e}")
    
    await session.commit()
    
    return {
        "message": f"Reset {reset_count} stuck documents",
        "reset_count": reset_count,
        "failed_count": failed_count,
        "documents_reset": [doc.filename for doc in stuck_docs[:reset_count]]
    }
