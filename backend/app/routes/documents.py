"""API routes for document upload and management"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
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
from app.config import settings
import os
import aiofiles
from pathlib import Path

router = APIRouter(prefix="/api/engagements/{engagement_id}/documents", tags=["documents"])

# Initialize services
doc_processor = DocumentProcessor(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap
)
embedding_service = EmbeddingService()
vector_store = get_vector_store()


@router.post("", response_model=MultiUploadResponse)
async def upload_documents(
    engagement_id: str,
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
            
            # Create document record
            document = Document(
                engagement_id=engagement_id,
                filename=file.filename,
                file_type=doc_processor.get_file_type(file.filename),
                file_size=file_size,
                file_path=str(file_path),
                status="processing"
            )
            
            session.add(document)
            await session.flush()  # Get document ID
            
            # Process document in background (simplified for now)
            try:
                # Extract text with metadata
                from io import BytesIO
                extraction_result = doc_processor.extract_with_metadata(BytesIO(file_content), file.filename)
                text = extraction_result['text']
                pages_info = extraction_result['pages']
                
                # Chunk text with page tracking
                chunks = doc_processor.chunk_text(
                    text,
                    metadata={
                        "document_id": document.id,
                        "filename": file.filename,
                        "engagement_id": engagement_id
                    },
                    pages_info=pages_info
                )
                
                if not chunks:
                    raise ValueError("No text extracted from document")
                
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
                
                results.append(UploadStatus(
                    filename=file.filename,
                    status="success",
                    message=f"Processed {len(chunks)} chunks",
                    document_id=document.id
                ))
                successful += 1
                
            except Exception as e:
                document.status = "failed"
                document.error_message = str(e)
                
                results.append(UploadStatus(
                    filename=file.filename,
                    status="failed",
                    message=f"Processing error: {str(e)}",
                    document_id=document.id
                ))
                failed += 1
            
        except Exception as e:
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
