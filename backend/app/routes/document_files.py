"""Document file serving endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import Document
from app.db_session import get_session
from app.services.file_storage import get_file_storage
from app.services.document_processor import DocumentProcessor
import io


router = APIRouter(prefix="/api/documents", tags=["document-files"])


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Serve document file for viewing"""
    # Get document from database
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Get file from storage
        file_storage = get_file_storage()
        file_content = await file_storage.get_file(document.file_path)
        
        # Determine content type
        content_type = "application/pdf"
        if document.file_type == "docx":
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif document.file_type == "txt":
            content_type = "text/plain"
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{document.filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving document: {str(e)}"
        )


@router.get("/{document_id}/preview")
async def get_document_preview(
    document_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get document text preview for non-PDF files"""
    # Get document from database
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Get file from storage
        file_storage = get_file_storage()
        file_content = await file_storage.get_file(document.file_path)
        
        # Extract text from document
        doc_processor = DocumentProcessor()
        text = doc_processor.extract_text(io.BytesIO(file_content), document.filename)
        
        return JSONResponse(content={
            "filename": document.filename,
            "text": text,
            "file_type": document.file_type,
            "file_size": document.file_size
        })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting document text: {str(e)}"
        )
