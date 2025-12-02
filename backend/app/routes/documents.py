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
from app.config import settings
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
            
            # Create document record - always queue for manual processing
            document = Document(
                engagement_id=engagement_id,
                filename=file.filename,
                file_type=doc_processor.get_file_type(file.filename),
                file_size=file_size,
                file_path=str(file_path),
                status="queued"  # Always queue
            )
            
            session.add(document)
            await session.flush()  # Get document ID
            
            logger.info(f"Document {document.id} queued for processing")
            
            results.append(UploadStatus(
                filename=file.filename,
                status="queued",
                message="Document uploaded successfully. Click 'Process Queued' to generate embeddings.",
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


# Legacy code path removed - keeping only queued pattern

        except Exception as e:
            # This except block is now unreachable but keeping for safety
            if False:
                pass  # Placeholder for removed legacy code


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
    """Delete a document"""
    document = await session.get(Document, document_id)
    
    if not document or document.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store
    await vector_store.delete_document(engagement_id, document_id)
    
    # Delete file from disk
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete from database
    await session.delete(document)
    await session.commit()
    
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
